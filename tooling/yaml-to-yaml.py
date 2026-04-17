# SPDX-FileCopyrightText: 2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
test script which tries to ensure an integration catalog entry
is valid YAML by reading from one and dumping into an other yaml file
"""

import yaml, argparse, pprint

parser = argparse.ArgumentParser()
parser.add_argument("-i","--infile", help="YAML input file - script will read the content of this file")
parser.add_argument("-o","--outfile", help="YAML output file - script will write the content to this file")
args = parser.parse_args()

# Reading data from the YAML file
with open(args.infile, 'r') as file:
    loaded_data = yaml.safe_load(file)

# write to new file
with open(args.outfile, 'w') as file:
    yaml.dump(loaded_data, file)
    
#print("Data read from 'data.yaml':")
#pprint.pp(loaded_data)


