'''
work work /orcpeon
'''

import json
from copy import deepcopy
from collections import defaultdict, Counter
import pandas as pd

FUZZ_AMT = 10
class NodeMetadata:
    
    def __cmp__(self, other):
        return self.__eq__(other)
    
    def __hash__(self):
        return hash(self._name + '!!' + self._intent)
    
    def __eq__(self, other):
        if type(other) == type(self):
            return other._name == self._name and \
                other._intent == self._intent
        return False
    
    def called(self):
        self._called += 1
        
    def get_func_intent_count(self):
        return self._func_count
        
    def get_data_intent_count(self):
        return self._data_count
        
    def set_func_intent_count(self, f_count):
        self._func_count = f_count
        
    def set_data_intent_count(self, d_count):
        self._data_count = d_count
        
    def get_called(self):
        return self._called
        
    def get_aliases(self):
        return self._aliases
        
    def get_intent(self):
        return self._intent
        
    def get_name(self):
        return self._name
    
    def set_called(self, called):
        self._called = called
    
    def set_aliases(self, aliases):
        self._aliases = aliases
    
    def set_intent(self, intent):
        self._intent = intent
    
    def set_name(self, name):
        self._name = name
    
    def __init__(self):
        self._called = 1
        self._name = ''
        self._intent = ''
        self._aliases = []
        self._func_count = 0
        self._data_count = 0

def read_data(floc):
    data = ''
    
    with open(floc, 'r') as f:
        data = f.read()
    
    return json.loads(data)

def fuzz(node):
    maxdepth = 0
    for n in node:
        trgt = node[n]
        if type(trgt) == dict:
            depth = fuzz(node[n])
            if depth > maxdepth:
                maxdepth = depth
        elif type(trgt) == list:
            for n1 in node[n]:
                depth = fuzz(n1)
                if depth > maxdepth:
                    maxdepth = depth
    node['maxdepth'] = maxdepth
    return maxdepth + 1

#expression 1 deep w/ name 1 deep -> <obj>.<thing>
#Basically pulls certain leaf nodes into the parent node
#We do this to make some data more accessible
#Every node has pos, end, flags. Most have kind as well.
def collapse_names(node, _search=False):
    cur_depth = node['maxdepth']
    ignore_types = ['pos', 'end', 'flags', 'kind', 'maxdepth', 'modifierFlagsCache']
    valid_subtypes = ['expression', 'name']
    
    if (not 'name' in node) or (not 'expression' in node) or ('escapedText' not in node['name'])\
     or ('escapedText' not in node['expression']):
        for n in node:
            trgt = node[n]
            if type(trgt) == dict:
                collapse_names(node[n])
            elif type(trgt) == list:
                for n1 in node[n]:
                    collapse_names(n1)
                    
    elif 'name' in node and 'expression' in node and cur_depth == 1:
        tname = node['expression']['escapedText'] + '.' + node['name']['escapedText']
        node['name']['escapedText'] = tname
        return tname
    elif 'expression' in node and 'name' in node:
        partialname = collapse_names(node['expression'], _search=True)
        if not partialname: return
        if not _search:
            node['name']['escapedText'] = partialname + '.' + node['name']['escapedText']
        else:
            return partialname + '.' + node['name']['escapedText']
    else:
        pass
                
'''
We're focusing on the structure around variables right now
Thus, we isolate:
1) The variable name
2) Variable data on how the variable is _used_ (is it invoked like an object? a function?)
3) Variable metadata (# of aliases, # of invocations, etc)
4) Information which lets LSTMs, RNNs, etc infer the current state of the "meaning" w.r.t. the variable
    e.g. include when we open or close brackets, or when enter an if statement
'''

#Is trying to build a list of aliases a fool's affair?
#How do you determine what an alias is?
#What happens if you have var a = generateBlank() + generateBlank() + b + generateBlank()
#if b is a string? Good for functions though.
def is_alias(node):
    return 'kind' in node and node['kind'] == 202 and 'left' in node \
            and 'right' in node and 'operatorToken' in node \
            and 'kind' in node['operatorToken'] \
            and node['operatorToken']['kind'] == 58 \
            and ('name' in node['left'] or \
                 'escapedText' in node['left']) \
            and ('name' in node['right'] or \
                 'escapedText' in node['right'])
            
def extract_alias_names(node):
    trgt = node
    _left = trgt['left']
    _right = trgt['right']
    left_text = ''
    right_text = ''
    if 'escapedText' in _left: left_text = _left['escapedText']
    elif 'name' in _left and 'escapedText' in _left['name']: left_text = _left['name']['escapedText']
    if 'escapedText' in _right: right_text = _right['escapedText']
    elif 'name' in _right and 'escapedText' in _right['name']: right_text = _right['name']['escapedText']
    return left_text, right_text
            
def build_alias_list_single(node, aliases=None):
    if not aliases:
        aliases = defaultdict(str)
    
    #We define an alias as expression: left (depth<=1), op (kind=58), right (depth<=1)
    node_is_alias = False
    if is_alias(node):
        #We have an alias!
        left_name, right_name = extract_alias_names(node)
        if left_name and right_name:
            node_is_alias = True
            aliases[left_name] = right_name
            aliases[right_name] = left_name
    if not node_is_alias:
        for n in node:
            trgt = node[n]
            if type(trgt) == dict:
                aliases = build_alias_list_single(node[n], aliases)
            elif type(trgt) == list:
                for n1 in node[n]:
                    aliases = build_alias_list_single(n1, aliases)
    
    return aliases
        
def build_alias_list(statements):
    
    aliases = []
    for v in statements:
        fuzz(v)
        collapse_names(v)
        _aliases = build_alias_list_single(v)
        for x in _aliases:
            trgt = _aliases[x]
            found = False
            for c in aliases:
                if trgt in c:
                    found = True
                    c.append(x)
                elif x in c:
                    found = True
                    c.append(trgt)
            if not found:
                aliases.append([x, trgt])
    
    aliases = [list(set(x)) for x in aliases]
    
    return aliases

def strip_aliases_single(node, aliases):
    for n in node:
        if type(node[n]) == dict:
            strip_aliases_single(node[n], aliases)
        elif type(node[n]) == list:
            for n1 in node[n]:
                strip_aliases_single(n1, aliases)
        elif n == 'escapedText' or n == 'text':
            for a in aliases:
                if node[n] in a:
                    node[n] = a[0]

def strip_aliases(statements, aliases):
    for v in statements:
        strip_aliases_single(v, aliases)
    
'''
Build our vocabulary
'''
        
def get_assignment_type(node):
    '''
    Type 1: `function foo(bar){}`
    Assign a function
    Root: 237
    has a name
    has parameters
    has a body
    '''
    
    if 'kind' in node and node['kind'] == 237 and 'parameters' in node and \
        'body' in node and 'name' in node:
        return 1
    
    '''
    Type 2: `foo = function(bar){}`
    Assign a function
    In declarationList -> declaration:
        kind: 235
        has a name
        has an initializer
            Kind: 194
            Has parameters
            Has body
    '''
    if 'kind' in node and node['kind'] in [235, 273] and 'name' in node and \
        'initializer' in node and 'kind' in node['initializer'] and \
        node['initializer']['kind'] in [194, 189, 203]:
        return 2
    
    '''
    Type 3: `foo = 'text'` 
    Assign a pre-existing object
    Kind: 202
    Has left
        left:
            has name
        right:
            has name w/ escapedText
    Has operatorToken
        kind: 58
    '''
    
    if 'kind' in node and node['kind'] == 202 and 'left' in node and \
        'name' in node['left'] and 'right' in node and 'name' in node['right'] \
        and 'escapedText' in node['right']['name'] and 'operatorToken' in node \
        and node['operatorToken']['kind'] == 58:
        return 3
    
    '''
    Type 4: `foo = 'text'` 
    Assign a text
    Kind: 202
    Has left
        left:
            has name
        right:
            has name w/ escapedText
    Has operatorToken
        kind: 58
    '''
    
    if 'kind' in node and node['kind'] == 202 and 'left' in node and \
        'escapedText' in node['left'] and \
        'right' in node and 'text' in node['right'] and \
        'operatorToken' in node and node['operatorToken']['kind'] == 58:
        return 4
    
    '''
    Type 5: `foo = function(){}` (other type) 
    Assign a function
    TODO: Define
    '''
    
    if 'kind' in node and node['kind'] == 202 and 'left' in node and \
        'name' in node['left'] and 'right' in node and 'arguments' in node['right'] \
        and 'operatorToken' in node and node['operatorToken']['kind'] == 58:
        return 5
    
    '''
    Type 6: `foo()` (other type) 
    Runs as a function
    Kind: 189
        has expression, arguments
    '''
    
    if 'kind' in node and node['kind'] == 189 and 'expression' in node \
        and 'arguments' in node and 'name' in node['expression']:
        return 6
    
    '''
    Type 7: `foo()` (other type) 
    Runs as a function (alt)
    Kind: 189
        has expression, arguments
    '''
    
    if 'kind' in node and node['kind'] == 189 and 'expression' in node \
        and 'arguments' in node and 'escapedText' in node['expression']:
        return 7
    
    return 0

def get_name_based_on_kind(node, kind):
    if kind == 1 or kind == 2:
        #Stored under name -> escapedText
        return node['name']['escapedText']
    elif kind == 4:
        #Stored under name -> escapedText
        return node['left']['escapedText']
    elif kind == 3 or kind == 5:
        #Stored under left -> name -> escapedText
        return node['left']['name']['escapedText']
    elif kind == 6:
        #Stored under left -> name -> escapedText
        return node['expression']['name']['escapedText']
    elif kind == 7:
        #Stored under left -> name -> escapedText
        return node['expression']['escapedText']
    
    return None
    
def build_variable_vocabulary_single(node, vocab=None, missing_names=None):
    if not vocab:
        vocab = defaultdict(list)
    if not missing_names:
        missing_names = []
        
    #Assign a variable
    kind = get_assignment_type(node)
        
    if kind:
        left_name = get_name_based_on_kind(node, kind)
        t_node = NodeMetadata()
        t_node.set_name(left_name)
        t_node.set_intent(kind)
        
        vocab[left_name].append(t_node)
    elif 'escapedText' in node and not (node['escapedText'] in vocab):
        k = ''
        if 'kind' in node:
            k = str(node['kind'])
            
        missing_names.append(node['escapedText'])
        
    for n in node:
        trgt = node[n]
        if type(trgt) == dict:
            vocab, missing_names = build_variable_vocabulary_single(node[n], vocab, missing_names)
        elif type(trgt) == list:
            for n1 in node[n]:
                vocab, missing_names = build_variable_vocabulary_single(n1, vocab, missing_names)
                
    return vocab, missing_names
        
def build_variable_vocabulary(statements):
    all_vocab = {}
    missing_names_all = []
    for v in statements:
        vocab, missing_names = build_variable_vocabulary_single(v)
        missing_names_all += missing_names
        
        for v1 in vocab:
            if v1 in all_vocab:
                all_vocab[v1] += vocab[v1]
            else:
                all_vocab[v1] = vocab[v1]
                
    missing_names_all = [x for x in missing_names_all if not x in all_vocab] 
    print(list(set(missing_names_all)))
    return all_vocab

def minimize_vocab(vocab, aliases):
    new_vocab = {}
    for v in vocab:
        vlist = vocab[v]
        filtered_intents = [x.get_intent() for x in vlist if x.get_intent() != 3]
        
        data_calls = 0
        func_calls = 0
        for instance in vlist:
            intent = instance.get_intent()
            if intent == 3: continue
            if intent == 4: 
                data_calls += 1
            else: 
                func_calls += 1
                
            
        new_metadata = NodeMetadata()
        new_metadata.set_name(v)
        
        new_metadata.set_func_intent_count(func_calls)
        new_metadata.set_data_intent_count(data_calls)
        
        local_aliases = []
        for a in aliases:
            if v in a:
                local_aliases = a
        new_metadata.set_aliases(list(set(local_aliases)))
        [new_metadata.called() for x in vlist]
        new_vocab[v] = new_metadata
    return new_vocab

def format_denoised_name(vocab, v, aliases):
    try:
        true_v = v
        for a in aliases:
            if v in a:
                true_v = a[0]
        v = true_v
        
        maxcalled = max([vocab[x].get_called() for x in vocab])
        maxalts = max([len(vocab[x].get_aliases()) for x in vocab])
        maxintent_data = max([vocab[x].get_data_intent_count() for x in vocab])
        maxintent_func = max([vocab[x].get_func_intent_count() for x in vocab])
        localized_intent_data = vocab[v].get_data_intent_count() + vocab[v].get_func_intent_count() + 1
        localized_intent_func = vocab[v].get_data_intent_count() + vocab[v].get_func_intent_count() + 1
        
        part_intent_data_max = str(round(vocab[v].get_data_intent_count() / float(maxintent_data), FUZZ_AMT))
        part_intent_func_max = str(round(vocab[v].get_func_intent_count() / float(maxintent_func), FUZZ_AMT))
        part_intent_data = str(round(vocab[v].get_data_intent_count() / float(localized_intent_data), FUZZ_AMT))
        part_intent_func = str(round(vocab[v].get_func_intent_count() / float(localized_intent_func), FUZZ_AMT))
        part_called = str(round(vocab[v].get_called() / float(maxcalled), FUZZ_AMT))
        part_aliases = str(round(len(vocab[v].get_aliases()) / float(maxalts), FUZZ_AMT))
        
        return '!'.join(['FUNC', 
                         part_intent_data, 
                         part_intent_func, 
                         part_called, 
                         part_aliases, 
                         part_intent_data_max,
                         part_intent_func_max])
        
    except KeyError as e:
        return 'UNKNOWN'

def sub_uniques_single(node, vocab, aliases):
    for n in node:
        if n == 'escapedText':
            newname = format_denoised_name(vocab, node[n], aliases)
            #print("New name: " + newname)
            node['escapedText'] = newname
        trgt = node[n]
        if type(trgt) == dict:
            sub_uniques_single(node[n], vocab, aliases)
        elif type(trgt) == list:
            for n1 in node[n]:
                sub_uniques_single(n1, vocab, aliases)
                
def sub_uniques(statements, vocab, aliases):
    for t in statements:
        sub_uniques_single(t, vocab, aliases)

def build_structural_metadata_single(node, kinds=None):
    if not kinds: kinds = []
    
    for n in node:
        if n == 'operatorToken':
            kinds.append(node[n]['kind'])
        elif n == 'escapedText' and node[n] == 'UNKNOWN':
            kinds.append('UNKNOWN')
        elif n == 'escapedText':
            if node[n].startswith('FUNC'):
                kinds.append('FUNC')
            elif node[n].startswith('DATA'):
                kinds.append('DATA')
        elif n == 'initializer':
            kinds.append('INIT')
        elif n == 'condition':
            kinds.append('COND')
        elif n == 'thenStatement':
            kinds.append('THEN')
        elif n == 'body':
            kinds.append('BODY')
        elif n == 'parameters':
            kinds.append('PARAM')
        elif n == 'declarations':
            kinds.append('DECL')
        elif n == 'finallyBlock':
            kinds.append('FINL')
        elif n == 'tryBlock':
            kinds.append('TRY')
        elif n == 'argument':
            kinds.append('ARG')
        elif n == 'catchClause':
            kinds.append('CATCH')
        elif n == 'variableDeclaration':
            kinds.append('VARDECL')
        elif n == 'block':
            kinds.append('BLOCK')
        elif n == 'left':
            kinds.append('LEFT')
        elif n == 'right':
            kinds.append('RIGHT')
        trgt = node[n]
        if type(trgt) == dict:
            kinds = build_structural_metadata_single(node[n], kinds)
        elif type(trgt) == list:
            for n1 in node[n]:
                kinds = build_structural_metadata_single(n1, kinds)
                
    return kinds

def build_structural_metadata(statements):
    metadata = []
    
    for v in statements:
        metadata += build_structural_metadata_single(v)

    metadata = Counter(metadata)
    metadata['all'] = sum([metadata[x] for x in metadata])

    return metadata

def emit_sequential_flat_single(node, structural_metadata, seq=None):
    if not seq: seq = []
    for n in node:
        tknFreq_all = structural_metadata['all']
        if n == 'escapedText' and node[n] == 'UNKNOWN':
            tknFreq = structural_metadata['UNKNOWN']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('UNKNOWN' + "!" + freq)
        elif n == 'escapedText':
            if node[n].startswith('FUNC'):
                tknFreq = structural_metadata['FUNC']
            else:
                tknFreq = structural_metadata['DATA']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append(node[n] + '!' + freq)
        elif n == 'operatorToken':
            tknFreq = structural_metadata[node[n]['kind']]
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append(str(node[n]['kind']) + "!" + freq)
        elif n == 'initializer':
            tknFreq = structural_metadata['INIT']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('INIT' + "!" + freq)
        elif n == 'condition':
            tknFreq = structural_metadata['COND']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('COND' + "!" + freq)
        elif n == 'thenStatement':
            tknFreq = structural_metadata['THEN']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('THEN' + "!" + freq)
        elif n == 'body':
            tknFreq = structural_metadata['BODY']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('BODY' + "!" + freq)
        elif n == 'parameters':
            tknFreq = structural_metadata['PARAM']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('PARAM' + "!" + freq)
        elif n == 'declarations':
            tknFreq = structural_metadata['DECL']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('DECL' + "!" + freq)
        elif n == 'finallyBlock':
            tknFreq = structural_metadata['FINL']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('FINL' + "!" + freq)
        elif n == 'tryBlock':
            tknFreq = structural_metadata['TRY']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('TRY' + "!" + freq)
        elif n == 'argument':
            tknFreq = structural_metadata['ARG']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('ARG' + "!" + freq)
        elif n == 'catchClause':
            tknFreq = structural_metadata['CATCH']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('CATCH' + "!" + freq)
        elif n == 'variableDeclaration':
            tknFreq = structural_metadata['VARDECL']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('VARDECL' + "!" + freq)
        elif n == 'block':
            tknFreq = structural_metadata['BLOCK']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('BLOCK' + "!" + freq)
        elif n == 'left':
            tknFreq = structural_metadata['LEFT']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('LEFT' + "!" + freq)
        elif n == 'right':
            tknFreq = structural_metadata['RIGHT']
            freq = str(round( tknFreq /float(tknFreq_all + 1) , FUZZ_AMT))
            seq.append('RIGHT' + "!" + freq)
        trgt = node[n]
        if type(trgt) == dict:
            seq = emit_sequential_flat_single(node[n], structural_metadata, seq)
        elif type(trgt) == list:
            for n1 in node[n]:
                seq = emit_sequential_flat_single(n1, structural_metadata, seq)
                
    return seq

def emit_sequential_flat(statements, structural_metadata):
    sequences = []
    for s in statements:
        sequences += emit_sequential_flat_single(s, structural_metadata)

    return sequences

def seq_to_pandas(sequence):
    colz = ['FUNC', 'DATA', 'UNKNOWN', 'KIND', 'INIT', 'COND', 
                               'THEN', 'BODY', 'PARAM', 'DECL', 'FINL', 'TRY',
                               'ARG', 'CATCH', 'VARDECL', 'BLOCK', 'LEFT', 'RIGHT',
                               'FREQ', 'INTENT_DATA', 'INTENT_FUNC', 'CALLED',
                               'ALIASES', 'INTENT_FUNC_MAX', 'INTENT_DATA_MAX']
    df = pd.DataFrame(columns=colz)
    for s in sequence:
        base_template = {c: 0. for c in colz}
        if s.startswith('FUNC!'):
            parts = s.split('!')
            intent_data = float(parts[1])
            intent_func = float(parts[2])
            called_count = float(parts[3])
            alias_count = float(parts[4])
            intent_data_max = float(parts[5])
            intent_func_max = float(parts[6])
            freq = float(parts[7])
            base_template['INTENT_DATA'] = intent_data
            base_template['INTENT_FUNC'] = intent_func
            base_template['CALLED'] = called_count
            base_template['ALIASES'] = alias_count
            base_template['INTENT_DATA_MAX'] = intent_data_max
            base_template['INTENT_FUNC_MAX'] = intent_func_max
            base_template['FREQ'] = freq
        else:
            parts = s.split('!')
            calltype = parts[0]
            freq = float(parts[1])
            base_template[calltype] = 1.
            base_template['FREQ'] = freq
        df = df.append(base_template, ignore_index=True)
    return df.fillna(0.)

floc = 'tew.json'
data = ''

with open(floc, 'r') as f:
    data = f.read()

t = json.loads(data)

aliases = build_alias_list(t)
strip_aliases(t, aliases)
vocab = build_variable_vocabulary(t)
min_vocab = minimize_vocab(vocab, aliases)
sub_uniques(t, min_vocab, aliases)
metadata = build_structural_metadata(t)
sequences = emit_sequential_flat(t, metadata)
pdc = seq_to_pandas(sequences)
print(list(pdc['FREQ']))
