# SPDX-FileCopyrightText: 2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Test script which converts a yaml into a python dict
and prints the content of the dict.

Can be used to ensure a yaml is properly structured.
"""

import yaml, argparse
from pprint import pprint

parser = argparse.ArgumentParser()
parser.add_argument("-i","--infile", help="YAML input file - script will read the content of this file")
parser.add_argument("-o","--outfile", help="python dict output file - script will write the content to this file")
args = parser.parse_args()

# Reading data from the YAML file
with open(args.infile, 'r') as file:
    loaded_data = yaml.safe_load(file)

# write to new file
with open(args.outfile, 'w') as file:
    pprint(loaded_data, stream=file)
    


