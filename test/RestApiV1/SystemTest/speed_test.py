#!/usr/bin/env python

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut
import json
import time
import sys

def main(argv):

    kwargs = \
    {
        "part_type_id": "Z00100300016",
        "serial_number": "%F%F%F%F%",
        "count": 100000,
    }
    outfile = "out.txt"

    print("Performing speed test")
    print("Test parameters:")
    print(json.dumps(kwargs, indent=4))

    start_time = time.time()
    resp = ut.fetch_hwitems(**kwargs)
    end_time = time.time()

    total_time = round(end_time - start_time, 3)

    print(f"records found: {len(resp)}")
    print(f"time: {total_time} seconds")
    
    with open(outfile, "w") as f:
        f.write(json.dumps(resp, indent=4))

    print(f"results written to '{outfile}'")

if __name__ == '__main__':
    sys.exit(main(sys.argv))
