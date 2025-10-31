"""
Globally silence the multiprocessing resource_tracker warning
and DeprecationWarnings across all modules and subprocesses.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Silence the 'leaked semaphore objects' warning in multiprocessing
try:
    import multiprocessing.resource_tracker as rt
    rt._resource_tracker._warn = lambda *a, **kw: None
except Exception:
    pass

# Make sure child processes inherit warning suppression
import os
os.environ["PYTHONWARNINGS"] = "ignore"
