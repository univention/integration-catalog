# SPDX-FileCopyrightText: 2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
test script which prints the content of a yaml file
can be used to ensure a yaml is properly structured
"""

import yaml, argparse, pprint

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="YAML input file, content will be printed to stdout")
args = parser.parse_args()

# Reading data from the YAML file
with open(args.infile, 'r') as file:
    loaded_data = yaml.safe_load(file)

print(f"Data read from {args.infile}:")
pprint.pp(loaded_data)
