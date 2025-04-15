#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/Utils/utils.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Miscellaneous utility functions
"""
import re
import os, sys
from functools import wraps


class objectmethod(classmethod):
    #{{{
    '''Permits a method to be used in both the class and instances of the class

    It behaves essentially like classmethod, except the first argument
    to the function (typically named 'cls') is only the class if called
    from the class. If called from an instance, it is the instance
    instead (typically named 'self').

    >>> class Example:
    ...     @objectmethod
    ...     def func(obj):
    ...         if type(obj) is type:
    ...             print("called from class")
    ...         else:
    ...             print("called from instance")
    ...
    >>> Example.func()
    called from class
    >>> Example().func()
    called from instance

    '''
    # I needed this sort of wrapper for some things I was doing with
    # the "Style" class, where I wanted to be able to chain properties,
    # e.g., Style.fg(0xFFFFFF).underline().bold(), where each method
    # call would return a new instance with the new property added to
    # the current instance, but I wanted the "classmethod" version to
    # make an empty instance to start with. Maybe someday, I'll rewrite
    # it better and we won't need this anymore.

    def __get__(self, instance, owner):
        if instance is None:
            return super().__get__(instance, owner)
        else:
            return self.__func__.__get__(instance, owner)
    #}}}

def process_list(fn):
    #{{{
    # TODO: probably obsolete
    def wrap(seq):
        print(seq)
        return list(map(fn, seq))
    setattr(wrap, "__name__", f"list<{fn.__name__}>")
    return wrap 
    #}}}

def traverse_dict(path):
    #{{{
    # TODO: probably obsolete
    def wrap(fn):
        def wrap(mp):
            print(mp, path)
            return fn(traverse(mp, path))
        
        #wrap.__name__ = f"Traverse<{fn.__name__}>"
        setattr(wrap, "__name__", f"traverse<{len(path)},{fn.__name__}>")
        return wrap 
    
    return wrap 
    #}}}

def normalize_path(path):
    #{{{
    """
    Resolve the path to a uniform standard. 
    Essentially the same as os.path.normpath, except, it also makes
    sure the drive letter is capitalized if we're in a windows system.
    
    Usage: see os.path.normpath()
    """

    newpath = os.path.normpath(path)

    # Check if the first two chars indicate the drive.
    # If so, make sure it's uppercase.
    if len(newpath)>2 and newpath[1] == ":":
        newpath = "".join([newpath[0].upper(), newpath[1:]])
    
    return newpath
    #}}}

def safe_add_to_path(*paths):
    #{{{
    """
    Checks sys.path for paths, and only inserts those that are not
    already there. Both paths and sys.path are normalized first, so
    equivalent paths will take the same form.
    """
    
    # map paths to their normalized version, so after we find out if
    # the path doesn't exist, we can add the *original* path, not 
    # the normalized one. If two paths are given that resolve to the
    # same normalized path, only the last one will be added.
    normalized_paths = {normalize_path(path): path for path in paths} 
    normalized_sys_paths = {normalize_path(path): path for path in sys.path}
    
    for norm, orig in normalized_paths.items():
        if norm not in normalized_sys_paths.keys():
            sys.path.append(orig)
    #}}}

def class_initializer(class_init=None):
    #{{{
    # TODO: I think this is obsolete now
    #@wraps(cls)
    def decorator_wrapper(cls):
        #setattr(cls, "_priv", [a, b, c])
        init_fn = getattr(cls, class_init, None) 
        if init_fn is None:
            msg = f"class {cls.__name__} does not have a class initializer {class_init}"
            logger.error(msg)
            raise TypeError(msg)
        elif not callable(init_fn):
            msg = f"class {cls.__name__}'s initializer {class_init} is not callable."
            logger.error(msg)
            raise TypeError(msg)
        else:
            #print(f"calling {cls.__name__}'s initializer!")
            init_fn()
        return cls
    return decorator_wrapper
    #}}}

def traverse(container, path):
    #{{{
    """
    Traverses through a nested container of dicts and lists. (Or compatible
    mapping and sequence types.)

    Parameters
    ----------
    container : nested mapping (dict-like) and sequence (list-like) types
    
    path : a sequence of str and/or int that describes the route through the
           nested dict/list

    Returns
    -------
    node : Any
        the data found by traversing the given path

    """
    try:
        node = container
        for id_ in path:
            node = node[id_]
        return node
    except LookupError:
        raise LookupError(path)
    except TypeError:
        return 'bad'
        #print(path, container)
        raise TypeError(f"path '{path}' was not valid")
    #}}}

def preserve_order(obj):
    #{{{
    '''Recursively store the key order of any dictionaries found

    As of Python 3.6, dictionaries already preserve the order of their
    keys, but when uploading to the HWDB and downloading again, the
    order of the keys is not guaranteed to stay the same. So, add an
    extra "_meta" tag that contains the correct order.

    Lists always preserve order, so leave them alone (but still recurse
    through them).

    Use 'restore_order' after downloading from the HWDB to get the
    dictionaries back into the correct order.

    NOTE: this adds the _meta tags in-place, so 'obj' is actually
    changed. Make a copy if this is not desired!
    '''

    if type(obj) is list:
        for item in obj:
            preserve_order(item)
    elif type(obj) is dict:
        order = list(obj.keys())
        if "_meta" in order:
            order.remove("_meta")
            #order.append("_meta")

        # We have to make sure to skip the '_meta' tag, so we don't
        # recurse forever. Note that if there was already a '_meta' tag
        # before we added one, the order of its contents will not be
        # preserved.
        for key, item in obj.items():
            if key != '_meta':
                preserve_order(item)
        
        if "_meta" in obj:
            obj["_meta"] = obj.pop("_meta")       
        
        if len(order) > 1:
            if "_meta" in obj and obj["_meta"] is None:
                obj["_meta"] = {}
            obj.setdefault("_meta", {})["keys"] = order

    # Even though the change was made in-place, return the object anyway.
    # It simplifies the syntax when one wants to make a copy:
    #     mycopy = preserve_order(deepcopy(original))
    return obj
    #}}}

def restore_order(obj):
    #{{{
    """Re-order the keys in dictionaries to saved order

    If the "_meta" tag only contains "keys", the entire "_meta" tag
    will be removed. Otherwise, only the "keys" will be removed.

    NOTE: this does the reordering
    """

    if type(obj) is list:
        for item in obj:
            restore_order(item)
    elif type(obj) is dict:
        if "_meta" in obj and isinstance(obj["_meta"], dict) and "keys" in obj["_meta"]:
            # Get the preserved ordering, but then look for any extra
            # keys that might have been added and add those to the list
            # at the end. At the time this comment was written, this
            # shouldn't happen, but I'd like it to go smoothly and not
            # drop data if this should happen in the future.
            order = obj["_meta"]["keys"]

            for key in order:
                if key not in obj:
                    order.remove(key)
            for key in obj.keys():
                if key not in order:
                    order.append(key)

            # Re-order the dictionary by popping each item and re-adding
            # it, which will place it at the end.
            for key in order:
                obj[key] = obj.pop(key)

            obj['_meta'].pop("keys")
            if len(obj['_meta']) == 0:
                obj.pop('_meta')


        for key, item in obj.items():
            restore_order(item)

    # Even though the change was made in-place, return the object anyway.
    # It simplifies the syntax when one wants to make a copy:
    #     mycopy = restore_order(deepcopy(original))
    return obj
    #}}}

def scramble_order(obj):
    #{{{
    '''Scramble the order of keys in dictionaries

    This function serves only as a test to simulate what might happen
    to an object that was uploaded to the HWDB and downloaded again.
    '''

    if type(obj) is list:
        for item in obj:
            scramble_order(item)
    elif type(obj) is dict:
        keys = list(obj.keys())

        # Shuffle the keys
        # if there are at least two keys, make sure the shuffle
        # actually changes the order. Redo if it doesn't.
        if len(keys) > 1:
            original_order = keys[:]
            while keys == original_order:
                random.shuffle(keys)
        for key in keys:
            obj[key] = obj.pop(key)
        for key, item in obj.items():
            scramble_order(item)

    # Even though the change was made in-place, return the object anyway.
    # It simplifies the syntax when one wants to make a copy:
    #     mycopy = scramble_order(deepcopy(original))
    return obj
    #}}}

def postgresql_pattern(expr):
    #{{{
    '''Create a regular expression pattern object from postgresql wildcards

    This is just a quick-and-dirty substitution. It probably could be
    fooled on purpose, but it's not likely to happen under normal
    usage.
    '''

    new_expr = (expr
                    .replace('.', '\\.')
                    .replace('*', '\\*')
                    .replace('(', '\\(')
                    .replace(')', '\\)')
                    .replace('_', '.')
                    .replace('%', '.*')
                )

    return re.compile('^' + new_expr + '$')
    #}}}

def serialize_for_display(obj):
    if isinstance(obj, dict):
        newobj = {}
        for key, value in obj.items():
            if isinstance(key, tuple):
                key = str(key)
            newobj[key] = serialize_for_display(value)
        return newobj
            
    elif isinstance(obj, list):
        newobj = []
        for value in obj:
            newobj.append(serialize_for_display(value))
        return newobj

    elif isinstance(obj,  (str, float, int, bool, type(None))):
        return obj

    else:
        return str(obj)            




if __name__ == '__main__':
    import doctest
    doctest.testmod()











