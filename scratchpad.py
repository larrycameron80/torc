#Dumping for just for reference

def drill2(v):
	data = []
	variables = []
	alias = []
	dropz = ['console', 'window', 'document', 'navigator']
	drill(v, data, variables, alias)
	return data, [x for x in variables if not x in dropz]

def drill(v, data, variables, alias):
	for k in v:
		if 'declarationList'  == k:
			for p in v['declarationList']['declarations']:
				drill(p, data, variables, alias)
		elif 'statements' == k:
			for p in v['statements']:
				drill(p, data, variables, alias)
		elif 'arguments' == k:
			for p in v['arguments']:
				drill(p, data, variables, alias)
		elif 'declarations' == k:
			drill(v['declarations'], data, variables, alias)
		elif 'left' == k:
			drill(v['left'], data, variables, alias)
		elif 'initializer' == k:
			data.append("init")
			drill(v['initializer'], data, variables, alias)
		elif 'right' == k:
			drill(v['right'], data, variables, alias)
		elif 'name' == k:
			drill(v['name'], data, variables, alias)
		elif 'expression' == k:
			drill(v['expression'], data, variables, alias)
		elif 'body' == k:
			drill(v['body'], data, variables, alias)
		elif 'argumentExpression' == k:
			drill(v['argumentExpression'], data, variables, alias)
		elif 'escapedText' == k:
			data.append(v['escapedText'])
			variables.append(v['escapedText'])
		elif 'text' == k:
			data.append(v['text'])
		elif 'operatorToken' == k:
			data.append(v['operatorToken']['kind'])

def drill(v, data, variables, alias):
	dropz = ['console', 'window', 'document', 'navigator']
	for k in v:
		if type(v[k]) == list:
			for p in v[k]:
				drill(p, data, variables, alias)
		elif type(v[k]) == dict:
			drill(v[k], data, variables, alias)
		elif 'escapedText' == k and v['escapedText'] not in dropz:
			data.append(v['escapedText'])
			variables.append(v['escapedText'])
		elif 'text' == k and v['text'] not in dropz:
			data.append(v['text'])
		elif 'operatorToken' == k:
			data.append(v['operatorToken']['kind'])


def dealias(v, aliaslist):
	data = []
	drill_dealias(v, data, aliaslist)
	return data


def drill_dealias(v, data, alias, in_argument=False, func_assign=True, obj_assign=True):
	dropz = ['console', 'window', 'document', 'navigator']
	for k in v:
		if k == 'argumentExpression':
			data.append('OP!ARG_EXP')
			in_argument = True
		elif k == 'arguments':
			data.append('OP!ARG_EXP_LIST')
			in_argument = True
		elif k == 'left':
			data.append('OP!' + str(in_argument) + '_LEFT')
		elif k == 'right':
			data.append('OP!' + str(in_argument) + '_RIGHT')
		if type(v[k]) == list:
			for p in v[k]:
				t_func = ('kind' in v and v['kind'] == 237) or ('kind' in v and v['kind'] == 189 and k != 'arguments') 
				t_func_obj = ('kind' in v and v['kind'] == 202)
				drill_dealias(p, data, alias, in_argument, t_func, t_func_obj)
		elif type(v[k]) == dict:
			t_func = ('kind' in v and v['kind'] == 237) or ('kind' in v and v['kind'] == 189 and k != 'arguments') 
			t_func_obj = ('kind' in v and v['kind'] == 202)
			drill_dealias(v[k], data, alias, in_argument, t_func, t_func_obj)
		elif 'escapedText' == k and v['escapedText'] not in dropz:
			found = False
			for a in alias:
				if v[k] in a:
					found = True
					val = a[0]
					if func_assign:
						val = 'FUNCNAME!' + val
					elif obj_assign:
						val = 'OBJ!' + val
					elif 'kind' in v and v['kind'] == '9':
						val = 'TEXT!' + val
					data.append(val)
			if not found:
				val = v[k]
				try:
					float(v[k])
					val = '<NUMBER>'
				except: pass
				if func_assign:
					val = 'FUNCNAME!' + val
				elif obj_assign:
					val = 'OBJ!' + val
				elif 'kind' in v and v['kind'] == '9':
					val = 'TEXT!' + val
				data.append(val)
		elif 'text' == k and v['text'] not in dropz:
			found = False
			for a in alias:
				if v[k] in a:
					found = True
					val = a[0]
					if func_assign:
						val = 'FUNCNAME!' + val
					elif obj_assign:
						val = 'OBJ!' + val
					elif 'kind' in v and v['kind'] == '9':
						val = 'TEXT!' + val
					data.append(val)
			if not found:
				val = v[k]
				try:
					float(v[k])
					val = '<NUMBER>'
				except: pass
				if func_assign:
					val = 'FUNCNAME!' + val
				elif obj_assign:
					val = 'OBJ!' + val
				elif 'kind' in v and v['kind'] == '9':
					val = 'TEXT!' + val
				data.append(val)
		elif 'kind' in v and v['kind'] == 58:
			data.append('OP!OP_EQ')


import json
floc = 'tewrwwa.json'
floc = 'tew.json'
data = ''

with open(floc, 'r') as f:
	data = f.read()

t = json.loads(data)

lines = []
for d in t:
	lines.append(drill2(d))

#Group the variables
varz = [x[1] for x in lines]
eqz = []
for var in varz:
	if len(var) == 2:
		v1, v2 = var
		grouped = False
		for s in eqz:
			if v1 in s and not (v2 in s):
				s.append(v2)
				grouped = True
			elif v2 in s and not (v1 in s):
				s.append(v1)
				grouped = True
			elif v1 in s and v2 in s: 
				break
		if not grouped:
			eqz.append([v1, v2])

alias = eqz

dealiased = []
for c in t:
	dealiased.append(dealias(c, alias))

funcz = {}
for line in dealiased:
	for entry in line:
		if entry.startswith('FUNCNAME!'):
			funcz[(re.sub('FUNCNAME!', '', entry))] = [re.sub('FUNCNAME!', '', entry)]

for f in funcz:
	for e in eqz:
		if f in e:
			funcz[f] = e

tags = ['OP', 'FUNCNAME']
elabtags = ['FUNCNAME']
slimmed = []
from collections import defaultdict
call_amt = defaultdict(int)
for part in dealiased:
	t_slimmed = []
	for x in part:
		if len(x.split('!')) == 2 and x.split('!')[0] in tags:
			if x.split('!')[0] in elabtags:
				t_slimmed.append(x)
				#t_slimmed.append(x.split('!')[0])
				call_amt[x.split('!')[1]] += 1
			else:
				t_slimmed.append(x)
		else:
			found = False
			for f in funcz.items():
				if x in f:
					t_slimmed.append('FUNCNAME!' + f[0])
					call_amt[f[0]] += 1
					found = True
			if not found:
				t_slimmed.append(x)
	slimmed.append(t_slimmed)

alls = []
for x in slimmed:
	for y in x:
		t_y = y
		if y.split('!')[0] in elabtags:
			t_y = y.split('!')[0] + "!" + str(call_amt[y.split('!')[1]])
		alls.append(t_y)
