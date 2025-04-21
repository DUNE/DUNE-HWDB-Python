#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.Configuration as cfg # for config's keywords and exceptions

from .exceptions import *
from .keywords import *

import threading
import requests

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import MessageBox
import sys

from copy import copy

import subprocess
import os

###############################################################################

class ProfileManager:
    def __init__(self, profile):
        logger.debug(f"STARTING ProfileManager.__init__ profile={profile.profile_name}")
        self.profile = profile
        self.lock = threading.RLock()

        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_CERT:
            logger.debug(f"{profile.profile_name} is using certificates.")
            return

        self.bearer_token = self.load_token()

        if self.bearer_token is None:
            # The file was empty. We need to refresh so the file can be
            # created and re-read
            self.refresh()
        
        logger.debug("FINISHED ProfileManager.__init__ profile={profile.profile_name}")


    def refresh(self):
        # We need the old_bearer_token so we can see if the ProfileManager
        # has already been refreshed, by comparing the old to the new.
        old_bearer_token = self.bearer_token

        with self.lock:
            if self.bearer_token == old_bearer_token:
                # If they're the same, it means that it hasn't been refreshed
                # yet, so we need to do it.

                # Do Refresh Action
                refresh_token(self.profile)

                # Reload
                self.bearer_token = self.load_token()

            if self.bearer_token is None:
                raise RestApiException("Unable to obtain bearer token")


    def load_token(self):
        try:
            with open(self.profile.bearer_token_file, 'r') as fp:
                return fp.read().strip()
        except FileNotFoundError as err:
            return None



class SessionManager:
    '''handles requests.Session objects on a per-thread & per-profile basis'''
    #
    # Explanation of the RestApiSession class
    # =======================================
    # RestApi calls will always try to grab a RestApiSession before making the
    # request. The big trick that RestApiSession must do is decide whether it 
    # should create a new Session (from the requests library) or return an 
    # existing one.
    #
    # Python docs suggest that multiple threads should not share the same
    # Session object, so the rule will be that each thread should have its own
    # RestApiSession. It is also possible for the same thread to try using
    # more than one config profile (which defines which RestApi server to 
    # connect to), so we have to use (thread_id, profile) as the unique key.
    #
    # We also need a mechanism to invalidate sessions once any request using
    # the same profile hits a "signature expired" from the server. To be
    # clear, this means that if one thread using profile "A" hits a 
    # "signature expired," then *all* threads using profile "A" must be
    # invalidated. However, only *one* of them should to refresh htgettoken.
    # The rest of them should be locked out until the refresh is complete.
    # Then, they can pick up the new bearer token and continue.
    #
    # =========================================================================

    _cached_sessions = {}
    _profile_managers = {}

    # Since _profile_managers is shared by multiple sessions which may be on 
    # multiple threads, we must make sure to lock other threads out whenever
    # operating on a node in _profile_managers
    _profile_lock = threading.RLock()

    def __new__(cls, profile):
        # There's sort of an implied "thread" parameter here, but we can get
        # that from the current thread
        current_thread = threading.current_thread()

        # The session_key uniquely defines the RestApiSession in the cache.
        # Note that we don't need to worry about multiple threads trying to
        # work with the same RestApiSession at the same time, because by
        # definition, each RestApiSession is tied to exactly one thread.
        session_key = (current_thread, profile.profile_name)

        if session_key in cls._cached_sessions:
            return cls._cached_sessions[session_key]
        else:
            new_obj = super().__new__(cls)
            cls._cached_sessions[session_key] = new_obj
            return new_obj

    def __init__(self, profile):

        if getattr(self, '_initialized', False):
            return

        self.current_thread = threading.current_thread()
        self.profile = profile
        self.session_key = (self.current_thread, self.profile.profile_name)

        # Create the requests.Session object
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        self._session.mount(f'https://{self.profile.rest_api}', adapter)

        # Handle "certificate" case
        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_CERT:
            self._session.cert = self.profile.authentication[cfg.KW_CERTIFICATE]

        # Handle "htgettoken" case
        elif self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_AUTH_HTGETTOKEN:
            self._last_bearer_token = None

        # No authorization set in configuration!
        else:
            raise cfg.ConfigurationError(f"profile {self.profile.profile_name!r} "
                    "has an invalid or missing authentication type.")

        self._initialized = True

    @property
    def session(self):
        if self.profile.authentication[cfg.KW_AUTH_TYPE] == cfg.KW_CERTIFICATE:
            # Since certificates don't expire frequently like htgettoken tokens
            # do, just return the session object with no worries
            return self._session
        
        if self.bearer_token != self._last_bearer_token:
            # The bearer token has changed, so update session headers!
            self._session.headers.update({
                'Authorization': f"Bearer {self.bearer_token}"
            })
            
            self._last_bearer_token = self.bearer_token
        return self._session
                

    @property
    def profile_manager(self):
        # Lock all profile data so that if a new profile needs to be created,
        # only one thread will do the creating.
        with self.__class__._profile_lock:
            profile_manager = self.__class__._profile_managers.get(self.profile.profile_name, None)
            if profile_manager is None:
                # we need to create it
                profile_manager = ProfileManager(self.profile)
                self.__class__._profile_managers[self.profile.profile_name] = profile_manager
            
            return profile_manager

    @property
    def bearer_token(self):
        with self.__class__._profile_lock:
            mgr = self.profile_manager
            return mgr.bearer_token
            

class output_so_far:
    #{{{
    def __init__(self, fp):
        self.fp = fp

        self.buffer = bytes()
        self.closed = False
        self.lock = threading.Lock()
        self.read_thread = threading.Thread(target=self._worker_task, daemon=True)
        self.read_thread.start()

    def _worker_task(self):
        while True:
            ch = self.fp.readline()
            if ch == b'':
                break
            with self.lock:
                self.buffer += ch
        self.closed = True

    def read(self):
        with self.lock:
            return copy(self.buffer)

    def read_all(self):
        self.read_thread.join()
        return copy(self.buffer)
        failed = False
        try:
            outs, errs = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            outs, errs = proc.communicate()
    #}}}

def refresh_token(profile):
    #{{{
    #.....................................................................
    def create_proc():
        #{{{
        config_dir = profile.profile_dir
        vault_token_file = profile.vault_token_file
        bearer_token_file = profile.bearer_token_file

        tokens = [
            #'python',
            #'-u',
            'hwdb-htgettoken',
            '-q',
            f'--configdir={config_dir}',
            f'--vaulttokenfile={vault_token_file}',
            f'--outfile={bearer_token_file}',
            '--vaultserver=htvaultprod.fnal.gov',
            '--issuer=fermilab',
            #'--web-open-command=',
        ]

        tokens.extend(profile.authentication.get('flags', []))
           
        try:
            proc = subprocess.Popen(
                        tokens,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        )
        except FileNotFoundError:
            msg = ("htgettoken not found. Have you installed it? "
                            "(try 'pip install htgettoken')")
            logger.error(msg)
            Style.error.print(msg)
            raise
        return proc
        #}}}

    #.....................................................................
    def display_message(msg, time_elapsed):
        #{{{
        outer_width = 80
        inner_width = 78

        if threading.current_thread().name == "MainThread":
            erase_msg = "".join([
                    Style.cursor_abs_horizontal(1),
                    Style.erase_line
                ])

            sys.stdout.write(erase_msg)
            sys.stdout.flush()

        msg = ' \n '.join([Style.info(s) for s in msg.split('\n')])
        inner = MessageBox(
                    msg, 
                    width=inner_width, 
                    outer_border='normal', 
                    border_color=Style.info._fg)

        info = ' \n '.join([
            '',
            Style.warning(
            #f'The call to htgettoken is taking longer than expected. ({time_elapsed})'),
            f'The call to htgettoken is taking longer than expected.'),
            '',
            'htgettoken may have attempted to open a browser window. Use this',
            'window to complete your authentication.',
            '',
            'If a browser window has not opened (e.g., if you''re using ssh to',
            'access a server remotely), the following information outputted from',
            'htgettoken may contain a URL that can be used to complete the',
            'authentication.',
            '',
        ])

        msg2 = '\n'.join([info, inner])

        outer = MessageBox(
                    msg2, 
                    width=outer_width, 
                    outer_border='strong', 
                    border_color=Style.warning._fg)
        print(outer)
        #}}}
    #.....................................................................
    
    logger.warning("Refreshing tokens")
    
    proc = create_proc()

    osf_stdout = output_so_far(proc.stdout)
    osf_stderr = output_so_far(proc.stderr)

    timed_out = None
    #displayed_response = False
    interval = 10
    total_time = 0
    max_time = 120

    last_stdout = ""
    last_stderr = ""

    while True:
        timed_out = False
        try:
            proc.wait(interval)
            timed_out = False
        except subprocess.TimeoutExpired as err:
            timed_out = True

        if not timed_out:
            break

        total_time += interval
        if total_time >= max_time:
            break

        current_stdout = osf_stdout.read().decode('utf-8')
        current_stderr = osf_stderr.read().decode('utf-8')

        if current_stdout != last_stdout:
            display_message(current_stdout, total_time)
            last_stdout = current_stdout
        if current_stderr != last_stderr:
            display_message(current_stderr, total_time)
            last_stderr = current_stderr


    if timed_out:
        proc.kill()
    current_stdout = osf_stdout.read_all().decode('utf-8')
    current_stderr = osf_stderr.read_all().decode('utf-8')
    
    if proc.returncode is None:
        err = "The call to htgettoken timed out."
        msg = "".join(
                    [
                        err, '\n',
                        f"stdout: {current_stdout} ",
                        f"stderr: {current_stderr} ",
                    ])
        logger.error(msg)
        raise AuthenticationError(err)
    elif proc.returncode != 0:
        err = "The call to htgettoken failed."
        msg = "".join(
                    [
                        err, '\n',
                        f"stdout: {current_stdout} ",
                        f"stderr: {current_stderr} ",
                    ])
        logger.error(msg)
        raise AuthenticationError(err)

    msg = ("The call to htgettoken succeeded. "
            f"stdout: {current_stdout} "
            f"stderr: {current_stderr} ")
    logger.info(msg)

    #}}}    

if __name__ == "__main__":
    print("DEVELOPMENT")
    dev_session = SessionManager(config.get_profile("development"))
    print(f"{dev_session.session.headers}")


    print('\n\n')


    print("PRODUCTION")
    prod_session = SessionManager(config.get_profile("production"))
    print(f"{prod_session.session.headers}")


    print('\n\n')
