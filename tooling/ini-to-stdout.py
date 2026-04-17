# SPDX-FileCopyrightText: 2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Test script which converts an ini and prints the content of the
file in a structured way.
"""

import configparser, argparse, pprint

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="YAML input file, content will be printed to stdout")
args = parser.parse_args()

config = configparser.ConfigParser()
config.sections()
config.read(args.infile)

print(f"Data read from {args.infile}:")
pprint.pp({s:dict(config.items(s)) for s in config.sections()})
