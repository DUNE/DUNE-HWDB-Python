#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

import json
import base64, PIL.Image, io
import sys
import re
import functools
import threading
import concurrent.futures
NUM_THREADS = 50
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

#{{{
def parse_part_id(part_id):
    match = parse_part_id.regex.fullmatch(part_id)
    return match.groupdict() if match else None
setattr(parse_part_id, 'regex', re.compile(
    r'''(?x)^
        (?P<part_id>
            (?P<part_type_id>
                (?P<project_id>[a-zA-Z])
                (?P<system_id>[0-9]{3})
                (?P<subsystem_id>[0-9]{3})
                [0-9]{5}
            )
            -
            [0-9]{5}
        )
    $'''))

def parse_part_type_id(part_type_id):
    match = parse_part_type_id.regex.fullmatch(part_type_id)
    return match.groupdict() if match else None
setattr(parse_part_type_id, 'regex', re.compile(
    r'''(?x)^
        (?P<part_type_id>
            (?P<project_id>[a-zA-Z])
            (?P<system_id>[0-9]{3})
            (?P<subsystem_id>[0-9]{3})
            [0-9]{5}
        )
    $'''))
#}}}



class HWDBObject:
    #{{{
    @classmethod
    def caching(cls, dec_cls):
        #setattr(dec_cls, '_cache', {'from_decorator': None, dec_cls.__name__: None})
        setattr(dec_cls, '_cache', {})
        setattr(dec_cls, '_class_lock', threading.RLock())
        setattr(dec_cls, '_statistics', {
                "requested": 0,
                "created": 0,
                "empty": 0,
                "initialized": 0,
                "refreshed": 0,
                "served_from_cache": 0,
                "failed": 0,
            })
        return dec_cls
   
    _constructor_args = []

    def __new__(cls, **kwargs): 
        #{{{
        logger.debug(f"{HLD}{cls.__name__}.__new__({kwargs})")
        cls._statistics['requested'] += 1

        constructor_kwargs = {arg: kwargs.get(arg) for arg in cls._constructor_args}

        if len(constructor_kwargs) == 0:
            constructor_key = None
        elif len(constructor_kwargs) == 1:
            constructor_key = constructor_kwargs[cls._constructor_args[0]]
        else:
            constructor_key = tuple(constructor_kwargs.values())
        logger.debug(f"{HLD}constructor_key={constructor_key}")
        
        if None in constructor_kwargs.values():
            logger.debug(f"{HLD}returning empty {cls.__name__}")
            cls._statistics['empty'] += 1
            return super().__new__()

        # Prevent two different threads from accessing the cache at the
        # same time. If two threads come trying to create the same
        # part_type_id at the same time, only one will be able to create it,
        # and the other will get a reference to the same object from
        # the cache.
        with cls._class_lock:
            if constructor_key in cls._cache:
                logger.debug(f"{HLD}returning object from cache")
                cls._statistics['served_from_cache'] += 1
                # NOTE: just because we're returning an object from the
                # cache, it doesn't mean it won't try to call __init__!
                # So, __init__ has to keep track of whether it has 
                # already been initialized!
                return cls._cache[constructor_key]
            else:
                logger.debug(f"{HLD}creating new {cls.__name__} object")
                cls._statistics['created'] += 1
                new_obj = super().__new__(cls)
                cls._cache[constructor_key] = new_obj
                return new_obj
        #}}}
    
    def __init__(self, **kwargs): 
        #{{{
        logger.debug(f"{HLD}{self.__class__.__name__}.__init__({kwargs})")
        
        self.fwd_kwargs = {k: v for k, v in kwargs.items() if k == 'status_callback'}

        with self.__class__._class_lock:
            if not getattr(self, "_instance_lock", None):
                setattr(self, "_instance_lock", threading.RLock())
                setattr(self, "_initialized", False)

        with self._instance_lock:
            refresh = kwargs.get('refresh', False)
            if self._initialized and not refresh:
                logger.debug(f"{HLD}{self.__class__.__name__}.__init__({kwargs})"
                                    " - already initialized")
                return
            if refresh:
                self.__class__._statistics['refreshed'] += 1
                logger.debug(f"{HLD}{self.__class__.__name__}.__init__({kwargs})"
                                    " - refreshing")
            else:
                self.__class__._statistics['initialized'] += 1
                logger.debug(f"{HLD}{self.__class__.__name__}.__init__({kwargs})"
                                    " - initializing")

            # I don't see a problem with setting _initialized at the beginning
            # since it's only used here in __init__, and any thread that wants
            # to check this will be locked out until we exit this 'with' block.
            # The reason I want to set it here is in case this function exits
            # abnormally. If that happens, there's no sense in other threads
            # trying to initialize every time they try to get this hwitem.
            self._initialized = True

            constructor_kwargs = {arg: kwargs.get(arg) for arg in self.__class__._constructor_args}
            for k, v in constructor_kwargs.items():
                setattr(self, f"_{k}", v)

            self._futures = {}
            self._data = {}

            if None in constructor_kwargs.values():
                return

            self._start_queries(constructor_kwargs)

            logger.debug(f"{HLD}{self.__class__.__name__}.__init__({kwargs})"
                                " - finished initializing")
        #}}}            

    def _start_queries(self, constructor_kwargs):
        raise NotImplementedError('This must be implemented in the inherited class')

    def _get_results(self, future_name):
        with self._instance_lock:
            if future_name in self._futures:
                self._data[future_name] = self._futures[future_name].result()
                del self._futures[future_name]
            return self._data.get(future_name)
    #}}}


@HWDBObject.caching
class WhoAmI(HWDBObject):
    #{{{
    _constructor_args = [] # No args. Just get the whole list.
    
    def _start_queries(self, constructor_kwargs):
        self._futures = {
            "whoami": _executor.submit(
                                ra.whoami,
                                **constructor_kwargs,
                                **self.fwd_kwargs),
        }

    @property
    def data(self):
        return self._get_results('whoami')['data']
    #}}}

@HWDBObject.caching
class Institutions(HWDBObject):
    #{{{
    _constructor_args = [] # No args. Just get the whole list.
    
    def _start_queries(self, constructor_kwargs):
        self._futures = {
            "institutions": _executor.submit(
                                ra.get_institutions,
                                **constructor_kwargs,
                                **self.fwd_kwargs),
        }

    @property
    def data(self):
        return self._get_results('institutions')['data']
    #}}}

@HWDBObject.caching
class System(HWDBObject):
    #{{{
    _constructor_args = ['project_id', 'system_id']
    
    def _start_queries(self, constructor_kwargs):
        self._futures = {
            "system": _executor.submit(
                                ra.get_system,
                                **constructor_kwargs,
                                **self.fwd_kwargs),
        }

    @property
    def data(self):
        return self._get_results('system')['data']

    @property
    def system(self):
        return f"{self.system_name} ({self.system_id})"
    
    @property
    def system_id(self):
        return f"{self.data['id']:03d}"
    
    @property
    def system_name(self):
        return f"{self.data['name']}"
    #}}}

@HWDBObject.caching
class Subsystem(HWDBObject):
    #{{{
    _constructor_args = ['project_id', 'system_id', 'subsystem_id']
    
    def _start_queries(self, constructor_kwargs):
        self._futures = {
            "subsystem": _executor.submit(
                                ra.get_subsystem,
                                **constructor_kwargs,
                                **self.fwd_kwargs),
        }

    @property
    def data(self):
        return self._get_results('subsystem')['data']
    
    @property
    def subsystem(self):
        return f"{self.subsystem_name} ({self.subsystem_id})"
    
    @property
    def subsystem_id(self):
        return f"{self.data['subsystem_id']:03d}"
    
    @property
    def subsystem_name(self):
        return f"{self.data['subsystem_name']}"
    #}}}

@HWDBObject.caching
class ComponentType(HWDBObject):
    #{{{
    _constructor_args = ['part_type_id']   

    def _start_queries(self, constructor_kwargs):
        #{{{
        part_type_id_decomp = parse_part_type_id(constructor_kwargs['part_type_id'])

        if part_type_id_decomp is None:
            # The part_type_id was not a valid format!
            self.__class__._statistics['failed'] += 1
            msg = f"Invalid part_type_id: {part_type_id}"
            logger.error(f"{HLE}{msg}")
            raise ValueError(msg)

        # Get the data asynchronously. It will be the job of the 
        # @property methods to grab the result() from these and 
        # put the data where it needs to go. 
        self._futures = {
            "component": _executor.submit(
                                ra.get_component_type, 
                                part_type_id=part_type_id_decomp['part_type_id'],
                                **self.fwd_kwargs),
        }
        #}}}            

    @property
    def data(self):
        return self._get_results("component")['data']
    #}}}

@HWDBObject.caching
class HWItem(HWDBObject):

    _constructor_args = ['part_id']


    def _start_queries(self, constructor_kwargs):
        #{{{
        part_id_decomp = parse_part_id(constructor_kwargs['part_id'])

        if part_id_decomp is None:
            # The part_id was not a valid format!
            msg = f"Invalid part_id: {constructor_kwargs['part_id']}"
            logger.error(f"{HLE}{msg}")
            self.__class__._statistics['failed'] += 1
            raise ValueError(msg)

        # Get the data asynchronously. It will be the job of the 
        # @property methods to grab the result() from these and 
        # put the data where it needs to go. 
        self._futures = {
            "hwitem": _executor.submit(
                                ra.get_hwitem, 
                                part_id=part_id_decomp['part_id'],
                                **self.fwd_kwargs),
            "subcomp": _executor.submit(
                                ra.get_subcomponents, 
                                part_id=part_id_decomp['part_id'],
                                **self.fwd_kwargs),
            "locations": _executor.submit(
                                ra.get_hwitem_locations,
                                part_id=part_id_decomp['part_id'],
                                **self.fwd_kwargs),
            "qr_code": _executor.submit(
                                ra.get_hwitem_qrcode,
                                part_id=part_id_decomp['part_id'],
                                **self.fwd_kwargs),
            "component_obj": _executor.submit(
                                ComponentType, 
                                part_type_id=part_id_decomp["part_type_id"],
                                **self.fwd_kwargs),
            "system_obj": _executor.submit(
                                System, 
                                project_id=part_id_decomp["project_id"],
                                system_id=part_id_decomp["system_id"],
                                **self.fwd_kwargs),
            "subsystem_obj": _executor.submit(
                                Subsystem, 
                                project_id=part_id_decomp["project_id"],
                                system_id=part_id_decomp["system_id"],
                                subsystem_id=part_id_decomp["subsystem_id"],
                                **self.fwd_kwargs),
        }
        #}}}            

    @property
    def qr_code(self):
        #{{{
        with self._instance_lock:
            if self._data.get("qr_code_processed") is None:
                content = self._get_results("qr_code").content
        
                # Turn the 'content' into an image, crop it to the right size,
                # and save the cropped image's data as base85
                img_obj = PIL.Image.open(io.BytesIO(content))
                cropped_obj = img_obj.crop((40, 40, 410, 410))
                obj_bytes = io.BytesIO()
                cropped_obj.save(obj_bytes, format="PNG")
                qr_code = base64.b85encode(obj_bytes.getvalue()).decode('utf-8')

                self._data["qr_code_processed"] = qr_code
            return self._data.get("qr_code_processed", None) 
        #}}}
    
    @property
    def data(self):
        return self._get_results("hwitem")['data']

    @property
    def component_type(self):
        return self._get_results("component_obj")
    @property
    def system(self):
        return self._get_results("system_obj")
    @property
    def subsystem(self):
        return self._get_results("subsystem_obj")

    @property
    def subcomponents(self):
        return self._get_results("subcomp")['data']

    @property
    def locations(self):
        return self._get_results("locations")['data']

    def update(self):
        ...
    #}}}


def main():
    from Sisyphus.Utils.Terminal.Style import Style
    from Sisyphus.Utils.Terminal.Image import image2text
    
    title_style = Style.info.underline()
    debug_title_style = Style.debug.underline()

    # USE THIS if you want to receive messages from the RestApiV1 library as queries
    # are being processed.
    #status_callback = lambda msg: Style.debug.print(f"callback: {msg}", flush=True)
    #fwd_kwargs = {"status_callback": status_callback}
    fwd_kwargs = {}

    part_id = ''
    if len(sys.argv) > 1:
        part_ids = sys.argv[1:]

    ###############################
    ##
    ## OUTPUT PARTS LIST
    ##
    ###############################
    print()
    title_style.print("Parts List")
    print('\n'.join(part_ids))

    ################################################
    ##
    ## PERFORM A BUNCH OF SIMULTANEOUS QUERIES
    ##
    ################################################
    whoami_future = _executor.submit(WhoAmI, **fwd_kwargs)
    hwitems_future = [ (part_id, _executor.submit(HWItem, part_id=part_id, **fwd_kwargs))
                        for part_id in part_ids ]

    ########################################
    ##
    ## OUTPUT 'WHO AM I?'
    ## 
    ########################################

    # Get the result of the whoami query, waiting for it to finish if necessary.
    # Other 'futures' may still be in progress, but do not wait for them.
    whoami = whoami_future.result()

    print()
    title_style.print("Who Am I?")    
    Style.notice.print(json.dumps(whoami.data, indent=4))


    ########################################
    ##
    ## OUTPUT HWITEMS
    ## 
    ########################################

    # Get the results of the hwitem queries.
    # I thought about doing some checking whether each one was finished and
    # skipping past those that hadn't finished yet, but the way I wrote 
    # the HWItem class, it should return right away. It's the results _inside_
    # the class instance that may be waiting, and I didn't put anything in
    # that would tell you what is or isn't ready.
    hwitems = []
    for (part_id, future) in hwitems_future:
        try:
            hwitem = future.result()
            hwitems.append( (part_id, hwitem))
        except Exception as exc:
            hwitems.append( (part_id, exc))

    # Print the results for each part_id
    for (part_id, result) in hwitems:
        print()
        title_style.print(part_id)
        
        if isinstance(result, Exception):
            Style.error.print(f"Exception Type: {type(Exception)}")
            continue
        else:
            hwitem = result

        Style.info.print(f"System:    {hwitem.system.system}")
        Style.info.print(f"Subsystem: {hwitem.subsystem.subsystem}")

        Style.notice.print(json.dumps(hwitem.data, indent=4))

        print()
        title_style.print(f"{part_id} Component Type Info")
        Style.notice.print(json.dumps(hwitem.component_type.data, indent=4))
        
        print()
        title_style.print(f"{part_id} Subcomponents")
        Style.notice.print(json.dumps(hwitem.subcomponents, indent=4))

        print()
        title_style.print(f"{part_id} Locations")
        Style.notice.print(json.dumps(hwitem.locations, indent=4))

        print()
        title_style.print(f"{part_id} QR Code")
        print()
        print(image2text(
                    base64.b85decode(hwitem.qr_code), 
                    columns=37, 
                    allow_halfline=True,
                    background=0x000000))


    def object_statistics(obj_type):
        obj_type_name = obj_type.__name__
        print()
        Style.debug.print(f"{obj_type_name} cache keys:")
        Style.debug.print(list(obj_type._cache.keys()))
        print()
        Style.debug.print(f"{obj_type_name} statistics:")
        Style.debug.print(json.dumps(obj_type._statistics, indent=4))

    if False:
        print()
        debug_title_style.print(f"Execution Statistics")

        object_statistics(HWItem)
        object_statistics(ComponentType)
        object_statistics(System)
        object_statistics(Subsystem)
        object_statistics(WhoAmI)

if __name__ == '__main__':
    sys.exit(main())
