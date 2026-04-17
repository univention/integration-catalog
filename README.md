---
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: AGPL-3.0-only
SPDX-FileCopyrightText: 2026 Univention GmbH
---

# Nubus Integration Catalog



## About

The Integration Catalog for Univention Nubus is a collection of existing integrations between Applications or Services and the Univention Nubus Identity Management (IAM). The objective is to provide users of Univention Nubus an easy access to all existing Integrations, serving as examples for the usage as well as repository to select from directly installable implementations.

## Status

Currently the project is in an alpha status, collecting existing integrations and building a PoC for a catalog web service which will be part of the Univention Web pages.

## Directory Structure

All information in this repository is provided in the YAML format. The files are structured in the following directories:

* definitions: globally defined categories etc. which can be referred to in the entries
* organizations: information about persons or companies providing the integrations which can be referred in the entries
* entries: the actual catalog entries, each entry has a subdirectory with one YAML file and optionally multiple logos or images (product logos, screen-shots etc.)
* tooling: some scripts helping to check or produce the YAML files

## Contribution

The repository is open for contribution! If you know howtos or packaged integrations please open a Pull Request to add them - see the [Contribution Guide](https://github.com/univention/univention-corporate-server?tab=contributing-ov-file#readme) for details on the process.

If you want to add a new integration the following needs to be done:

* If needed add a new organization for yourself if you want to be visible in the integration catalog. This is needed if there is a commercial offering for the integration, otherwise it is recommended but optional (for example if you only want to link a nice howto but don't have the agreement of the author).
* Add a new subdirectory in "entries" with a unique name. In this directory
  * Add a new "YAML" file describing the integration following the examples of the other YAML files (a better definition will follow). Recommendation is to copy an existing YAML and edit it.
  * Add logos, images etc. which then can be referred to in the YAML file
* For all contributions ensure that you comply to licensing, copyrights and trademarks. For example if you copy descriptions or product logos check the license of the source or get a confirmation of the copyright owner.

## License
All files in this repository should contain a SPDX license header. Typically content is licensed under the AGPL, while the used product icons and images are often protected by trademark rights.

