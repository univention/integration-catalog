# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Script which reads an ini file describing an App in the
Univention App Center and generates a starting point for a
Univention Nubus Integration Catalog yaml entry file.

The created yaml isn't complete and needs additional information
before being used in the Integration Catalog. Needed changes are at least:
- formatting of the descriptions (convert HTML to Markdown)
- correct links to meta data: organization, capabilities, platforms, technologies etc.
"""

import configparser, argparse, pprint, yaml, os, sys, shutil
from urllib.request import urlretrieve

# pyhtml2md from pip3
import pyhtml2md

SPDXHEADER = "# SPDX-FileCopyrightText: 2026 Univention GmbH\n# SPDX-License-Identifier: AGPL-3.0-only\n\n"


def _getFilenamesFromThumbnailstring(thumbnailstring):
    thumbnails = thumbnailstring.split(",")
    filenames = []
    for thumbnail in thumbnails:
        if not thumbnail.strip().startswith("http"):
            filenames.append(thumbnail.strip())
    return filenames



parser = argparse.ArgumentParser()
parser.add_argument("infile", help="INI input file containing an App Center App INI description file")
parser.add_argument("outdir", help="Directory under which an App specific directory containing images and YAML output whill be stored. Sudirectory will be created if not exists, existing files will be overwritten.")
args = parser.parse_args()

if not os.path.isfile(args.infile):
    print("ERROR: infile %s does not exist or is not a file" % args.infile)
    sys.exit(1)

if not os.path.isdir(args.outdir):
    print("ERROR: outdir %s does not exist or is not a directory" % args.outdir)
    sys.exit(1)

# read ini file
iniConfig = configparser.ConfigParser()
iniConfig.sections()
iniConfig.read(args.infile)

# check if it supports UCS 5.2
#print ("VERSIONCHECK")
#print (iniConfig.get('Application', 'SupportedUCSVersions', fallback="5.2-0").split(","))

# the check fails for Apple Schoolmanager, opsi, OX Documents, OX App Suite, UCS Dashboard Client (and maybe more?)
if not iniConfig.get('Application','ID') in ["apple-school-manager", "opsi", "ox-connector", "oxseforucs", "open-xchange-text"]:
    try:
        next(obj for obj in iniConfig.get('Application', 'SupportedUCSVersions', fallback="5.2-0").split(",") if obj.strip().startswith("5.2-"))
    except StopIteration:
        print("ERROR: App %s does not support UCS 5.2-0" % iniConfig.get('Application','Name'))
        sys.exit(2)

# create empty dict structure for entry YAML
outDict = {
    'id': '', # internal global unique identifier
    'version': '', # latest release version, visible in the catalog. Can be empty (for example for HowTos)
    'main_icon': '', # icon in search results if localization not possible or no localized icon available
    'metadata': { # metadata about this entry, not about the integration
        'created_by': '',
        'creation_date': '',
        'last_update_date': ''
    },
    'organizational_specifications': { # references to "organizations" defined separately, all values are identifiers
        'support_contact_id': '',
        'support_status': '',
        'vendor_id': ''
    },
    'technical_specifications': { # references to technical parameters defined separately, all values are identifiers
        'capabilities': [],
        'compatible_platforms': [],
        'compatible_products': [],
        'dependencies': [], # dependencies on other integrations, identifier is an integration id
        'protocols': [
        ],
        'source_license': '',
    },
    'description': { # localized descriptions. At least en-US must be given, de-DE is expected.
        'de-DE': {
            'icon': '', # localized icon in search results
            'links': [ # one or several links to further information about the integration
                {'Description': '',
                 'URL': ''},
            ],
            'name': '', # very short name, for listings like search results
            'short_description': '', # short description for example in mouse over of search results
            'long_description': '', # long description for catalog detail page, can make use of HTML
            'tags': [], # tags, in contrast to keywords visualized in the catalog - empty for now, need further concepts later
            'keywords': [], # internal search keywords for the catalog
            'visuals': [] # list of large visuals for the catalog detail page, for example screenshots
        },
        'en-US': {
            'icon': '',
            'links': [
                {'Description': '',
                 'URL': ''},
            ],
            'long_description': '',
            'name': '',
            'short_description': '',
            'tags': [],
            'keywords': [],
            'visuals': []
        },
    },
}

# mapping from ini to dict

## global
outDict['id'] = f"UCSAPP-{iniConfig.get('Application','ID')}"
outDict['version'] = iniConfig.get('Application','Version')

## en-US - default in ini files
outDict['description']['en-US']['name'] = iniConfig.get('Application','Name')
outDict['description']['en-US']['short_description'] = pyhtml2md.convert(iniConfig.get('Application','Description', fallback=iniConfig.get('de','Description', fallback="NO DESCRIPTION FOUND")))
try:
    outDict['description']['en-US']['long_description'] = pyhtml2md.convert(iniConfig.get('Application','LongDescription'))
except:
    print("WARN: failed to parse LongDescription")
outDict['description']['en-US']['icon'] = iniConfig.get('Application','Logo',fallback="")
outDict['description']['en-US']['keywords'] = \
    iniConfig.get('Application','Categories',fallback="").split(', ') + \
    iniConfig.get('Application','AppCategories',fallback="").split(', ')
outDict['description']['en-US']['visuals'] += _getFilenamesFromThumbnailstring(iniConfig.get('Application','Thumbnails',fallback=""))

## de-DE - translation [de] in ini files
outDict['description']['de-DE']['name'] = iniConfig.get('de','Name',
                                                        fallback = iniConfig.get('Application','Name'))
outDict['description']['de-DE']['short_description'] = pyhtml2md.convert(iniConfig.get('de','Description',
                                                        fallback = outDict['description']['en-US']['short_description']))
try:
    outDict['description']['de-DE']['long_description']= pyhtml2md.convert(iniConfig.get('de','LongDescription',
                                                                       fallback = iniConfig.get('Application','LongDescription')))
except:
    print("WARN: failed to parse LongDescription")
outDict['description']['de-DE']['icon'] = iniConfig.get('de','Logo',
                                                        fallback = iniConfig.get('Application','Logo',fallback=""))
outDict['description']['de-DE']['keywords'] = \
    iniConfig.get('de', 'Categories',
                  fallback = iniConfig.get('Application', 'Categories',fallback="")).split(', ') + \
    iniConfig.get('de','AppCategories',
                  fallback = iniConfig.get('Application','AppCategories',fallback="")).split(', ')
outDict['description']['de-DE']['visuals'] += _getFilenamesFromThumbnailstring(iniConfig.get('Application','Thumbnails',fallback=""))


#print(f"Data read from {args.infile}:")
#pprint.pp({s:dict(config.items(s)) for s in config.sections()})

#print(f"dict generated from {args.infile}:")
#pprint.pp(outDict)

outfilename = outDict['id'] + ".yaml"
outsubdirname = outDict['id']
outdirpath = os.path.join(args.outdir, outsubdirname)
outfilepath = os.path.join(outdirpath, outfilename)

# create directory if needed
if not os.path.isdir(outdirpath):
    os.mkdir(outdirpath)

# write to new file
with open(outfilepath, 'w') as file:
    file.write(SPDXHEADER)
    yaml.dump(outDict, file, allow_unicode=True)

# copy logos and screenshots


sourcepath = os.path.dirname(args.infile)

# logo is always derived from .ini filename
logosourcefile = args.infile.replace(".ini",".logo")
logotargetfile = os.path.join( outdirpath, outDict['description']['en-US']['icon'] )
if os.path.isfile(logosourcefile):
    shutil.copy(logosourcefile, logotargetfile)
else:
    print("logo not found %s" % logosourcefile)

for filename in outDict['description']['en-US']['visuals'] + outDict['description']['de-DE']['visuals']:

    targetfilename = os.path.join( outdirpath, filename)
    if os.path.isfile(targetfilename):
        print("INFO: skip download as file exists: %s" % targetfilename)
        continue
    
    ucsversion = "5.2"
    try:
        next(obj for obj in iniConfig.get('Application', 'SupportedUCSVersions', fallback="5.2-0").split(",") if obj.startswith("5.0-"))
    except StopIteration:
        pass
    else:
        ucsversion = "5.0"

    url = "https://appcenter.software-univention.de/meta-inf/" + ucsversion + "/" + iniConfig.get('Application','ID') + "/" + filename
    try:
        urlretrieve(url, targetfilename)
    except:
        print("WARN: failed to get %s" % url)
                  
