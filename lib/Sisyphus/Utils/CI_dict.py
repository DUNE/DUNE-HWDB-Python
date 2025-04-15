#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

CI_dict: Case-Insensitive Dictionary
"""


class CI_dict(dict):
    '''Case-Insensitive Dictionary

    Behaves similarly to the built-in dict, except that it allows using
    alternative casing for keys that are strings.

    The dictionary retains the original keys in the original order, even
    though they can be accessed with alternative casing:

        >>> cid = CI_dict({'Abc': 3, 'Def': 6})
        >>> cid['abC']
        3
        >>> cid.keys()
        dict_keys(['Abc', 'Def'])

    Updating the value with different casing, however, will update the 
    casing of the key as well, although it will still preserve the order:

        >>> cid['abC'] = 4
        >>> cid.keys()
        dict_keys(['abC', 'Def'])

    A key will be considered 'in' the dictionary even if the casing is 
    different, but it will not be considered 'in' the keys() object itself:

        >>> 'abc' in cid
        True
        >>> 'abc' in cid.keys()
        False

    '''

    @staticmethod
    def _foldkey(key):
        return key.casefold() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize the map between lowercase and the actual key
        self._keymap = {}
        for key in super().keys():
            self._keymap[self._foldkey(key)] = key

    def __setitem__(self, key, value):

        # If the user supplied the key with a different case, we should
        # get rid of the old case, so there aren't two key value pairs
        # in the dict. E.g. myDict['aBC'] = 12 ; myDict['Abc'] = 13 should
        # get rid of the 'aBC' version before adding the 'Abc' version.
        
        renamed_key = False

        if self._foldkey(key) in self._keymap:
            if (prev_key_case := self._keymap[self._foldkey(key)]) != key:
                renamed_key = True
                super().__delitem__(prev_key_case)

        super().__setitem__(key, value)
        self._keymap[self._foldkey(key)] = key

        if renamed_key:
            for key_in_order in self._keymap.values():
                super().__setitem__(key_in_order, super().pop(key_in_order))
 
    def __getitem__(self, key):
        lc_key = self._foldkey(key)
        actual_key = self._keymap[lc_key]
        return super().__getitem__(actual_key)


    def __delitem__(self, key):
        lc_key = self._foldkey(key)
        actual_key = self._keymap[lc_key]
        del self._keymap[lc_key]
        super().__delitem__(actual_key)

    def get(self, key, default=None):
        if self._foldkey(key) in self._keymap:
            actual_key = self._keymap[self._foldkey(key)]
            return super().__getitem__(actual_key)
        else:
            return default

    def update(self, E=None, **F):
        if E:
            for k, v in E.items():
                self.__setitem__(k, v)
        for k, v in F.items():
            self.__setitem__(k, v)

    def pop(self, k, *args):
        key = self._foldkey(k) 
        if key in self._keymap:
            key = self._keymap.pop(key)
            
        return super().pop(key, *args)

    def __contains__(self, key):
        return self._foldkey(key) in self._keymap 

    def setdefault(self, key, default=None):
        if self._foldkey(key) in self._keymap:
            return self.__getitem__(key)
        else:
            self.__setitem__(key, default)
            return self.__getitem__(key)

    def clear(self):
        super().clear()
        self._keymap.clear()

    def popitem(self):
        retval = super().popitem()
        self._keymap.popitem()
        return retval

    def copy(self):
        return self.__class__(super().copy())

    @classmethod
    def fromkeys(cls, iterable, value=None, /):
        new_dict = super().fromkeys(iterable, value)
        return cls(new_dict)

    def rectify_keys(self, keys):
        '''Match the casing of keys to that found in the list of keys'''

        has_changed = False
        for key in keys:
            foldkey = self._foldkey(key)
            if foldkey in self._keymap:
                actual_key = self._keymap[key]
                if key != actual_key:
                    self._keymap[foldkey] = key
                    super().__setitem__(key, super().pop(actual_key))
                    has_changed = True
        if has_changed:
            # we need to repair the order of the true dictionary
            for key_in_order in self._keymap.values():
                super().__setitem__(key_in_order, super().pop(key_in_order))
        


def main():
    # perform a quick set of tests

    # do a test on docstring examples
    import doctest
    doctest.testmod()

    
    # the docstrings aren't intended to be comprehensive so the rest
    # of this is more detailed tests


    import json

    cid = CI_dict({'aBc': 11, 'dEf': 12, 100: 200})   

    # test that items can be accessed with alternate casing
    assert(cid['abc'] == 11)
    assert(cid['aBC'] == 11)
    assert(cid['DEF'] == 12)
    assert(cid['def'] == 12)
    assert(cid[100] == 200)
    assert(cid.get('abc') == 11)
    assert(cid.get('aBC') == 11)
    assert(cid.get('DEF') == 12)
    assert(cid.get('def') == 12)
    assert(cid.get(100) == 200)
    assert(cid.get('xyz') is None)
    assert(cid.get('pdq', -1) == -1)

    # keys have retained the same case and order
    assert(list(cid.keys()) == ['aBc', 'dEf', 100])

    # changing a value will update the case of the key, but not
    # alter the order of the keys
    cid['ABC'] = 13
    assert(list(cid.keys()) == ['ABC', 'dEf', 100])

    # deleting an item
    del cid['aBC']
    assert(list(cid.keys()) == ['dEf', 100])

    # update (with dict)
    cid.update({'DEF': 14, 'gHi': 15, 'abc': 16, 101: 87, 100: 201, 'JKl': 'apple'})
    assert(list(cid.keys()) == ['DEF', 100, 'gHi', 'abc', 101, 'JKl'])
    assert(list(cid.values()) == [14, 201, 15, 16, 87, 'apple'])

    # update (with key/value)
    cid.update(aBc = 17)
    assert(list(cid.keys()) == ['DEF', 100, 'gHi', 'aBc', 101, 'JKl'])
    assert(list(cid.values()) == [14, 201, 15, 17, 87, 'apple'])

    # pop
    assert(cid.pop('ABC') == 17)
    assert(cid.pop('xyz', -1) == -1)
    assert(list(cid.keys()) == ['DEF', 100, 'gHi', 101, 'JKl'])
    assert(list(cid.values()) == [14, 201, 15, 87, 'apple'])

    # popitem
    assert(cid.popitem() == ('JKl', 'apple'))
    assert(list(cid.keys()) == ['DEF', 100, 'gHi', 101])
    assert(list(cid.values()) == [14, 201, 15, 87])
    
    # __contains__
    assert('DEF' in cid)
    assert('DEF' in cid.keys())
    assert('def' in cid)
    assert(not ('def' in cid.keys()))
    assert('Def' in cid)
    assert(100 in cid)
    assert('GHI' in cid)

    # setdefault
    # calling setdefault with an existing key should not update casing
    assert(cid.setdefault('ghi', 100) == 15)    
    assert(list(cid.keys()) == ['DEF', 100, 'gHi', 101])
    assert(cid.setdefault('MnO', 18) == 18)

    # copy
    cidcopy = cid.copy()
    assert(type(cid) == type(cidcopy))
    cid['mno'] = 19
    assert(cid['Mno'] == 19)
    assert(cidcopy['Mno'] == 18)
    
    # clear
    cid.clear()
    assert(len(cid) == 0)

    # check integrity of the internal _keymap
    assert(len(cid._keymap) == 0)
    assert(list(cidcopy.keys()) == ['DEF', 100, 'gHi', 101, 'MnO'])
    assert(list(cidcopy.values()) == [14, 201, 15, 87, 18])
    assert(list(cidcopy._keymap.keys()) == ['def', 100, 'ghi', 101, 'mno'])
    assert(list(cidcopy.keys()) == list(cidcopy._keymap.values()))

    # new type remains json serializable
    # (note that integer keys are converted to strings. That's just what json does.)
    assert(json.dumps(cidcopy) == '{"DEF": 14, "100": 201, "gHi": 15, "101": 87, "MnO": 18}')

    # rectify_keys
    cidcopy.rectify_keys(['mno', 'def', 'ghi', 100])
    assert(list(cidcopy.keys()) == ['def', 100, 'ghi', 101, 'mno'])

if __name__ == "__main__":
    main()


