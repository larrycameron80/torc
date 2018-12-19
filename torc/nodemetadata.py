'''
Node metadata. 

Used when we encounter variable names in our AST.
Essentially, we're trying to deduce how variables are used. As a key part of
torc involves pulling data from all around the document in order to provide
document-wide data to the RNN as the RNN looks at set of lines, we use
NodeMetadata in order to keep track of what is what. Then, when it comes time,
we aggregate our metadata into a new metadata instance (needs to be split into
two different classes). The AST to torc translator then takes the metadata
and essentially replaces the appropriate variable or variables with the
metadata from this class as required.

In doing this, we effectively contextualize each variable in such a way that
the RNN has access to the way to the variable is used relative to both itself
as well as other variables present in the document.

Note: We have some extra functions and code present from an earlier version. 
Because this is still a proof of concept, I have not yet taken the time to
fully clean out old code from when I was exploring if this concept is event
feasible.
'''
import json, time, math, re
from copy import deepcopy
from collections import defaultdict, Counter
import pandas as pd

class NodeMetadata:
    
    def __cmp__(self, other):
        return self.__eq__(other)
    
    #do we really need __cmp__, __hash__, and __eq__?
    def __hash__(self):
        #This was for some earlier string-based metadata tags
        #We no longer use those tags but I need to check the AST translator
        #to ensure we do not directly or indirectly call this function.
        return hash(self._name + '!!' + self._intent)
    
    def __eq__(self, other):
        if type(other) == type(self):
            return other._name == self._name and \
                other._intent == self._intent
        return False
    
    def set_standards(self, vocab):
        maxcalled = max([vocab[x].get_called() for x in vocab]) + 1.
        maxalts = max([len(vocab[x].get_aliases()) for x in vocab]) + 1.
        maxintent_data = max([vocab[x].get_data_intent_count() for x in vocab]) + 1.
        maxintent_func = max([vocab[x].get_func_intent_count() for x in vocab]) + 1.
        localized_intent_data = self.get_data_intent_count() + self.get_func_intent_count() + 1
        localized_intent_func = self.get_data_intent_count() + self.get_func_intent_count() + 1
        
        #fuzz_amt is no longer needed, keeping around until a later update
        self._standard_intent_data_max = (round(self.get_data_intent_count() / float(maxintent_data), self._FUZZ_AMT))
        self._standard_intent_func_max = (round(self.get_func_intent_count() / float(maxintent_func), self._FUZZ_AMT))
        self._standard_intent_data = (round(self.get_data_intent_count() / float(localized_intent_data), self._FUZZ_AMT))
        self._standard_intent_func = (round(self.get_func_intent_count() / float(localized_intent_func), self._FUZZ_AMT))
        self._standard_called = (round(self.get_called() / float(maxcalled), self._FUZZ_AMT))
        self._standard_aliases = (round(len(self.get_aliases()) / float(maxalts), self._FUZZ_AMT))
        
    def get_standardized_intent_data(self):
        return self._standard_intent_data
    
    def get_standardized_intent_func(self):
        return self._standard_intent_func
    
    def get_standardized_called(self):
        return self._standard_called
    
    def get_standardized_aliases(self):
        return self._standard_aliases
    
    def get_standardized_intent_data_max(self):
        return self._standard_intent_data_max
    
    def get_standardized_intent_func_max(self):
        return self._standard_intent_func_max
    
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
    
    def __init__(self, fuzz_amount=10):
        self._called = 1
        self._name = ''
        self._intent = ''
        self._aliases = []
        self._func_count = 0
        self._data_count = 0
        self._FUZZ_AMT = fuzz_amount
