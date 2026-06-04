---
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: AGPL-3.0-only
SPDX-FileCopyrightText: 2026 Univention GmbH
---

# integration-catalog editor and tools

Python library, command-line tools, and graphical editor for managing the
Univention Nubus Integration Catalog.

The objective of these implementations is to simplify changes and maintenance
of the integration catalog. The tools are build in a "Best Effort" approach and
in an early stage, so they might lack features or stability in areas they are
not often used. Feel free to contribute!

The package provides three complementary interfaces to the same catalog data:

| Interface | Use case |
|---|---|
| **Python library** | Scripting, automation, custom tooling |
| **CLI** (`integration-catalog`) | Quick edits and validation from the terminal |
| **Web editor** (`integration-catalog-ui`) | Visual editing in a browser |

---

## Quickstart

### Prerequisites

- Python 3.11 or later
- An internet connection for the first-time package installation

### Installation

```bash
cd editor/integration_catalog
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

After installation two commands are available in your virtualenv:
`integration-catalog` (CLI) and `integration-catalog-ui` (web editor).

### Validate the catalog

```bash
integration-catalog --root /path/to/integration-catalog validate
```

### Launch the web editor

The easiest way to start is the provided shell script, which handles
virtualenv creation and dependency installation automatically:

```bash
# Linux / macOS
./start-ui.sh

# Windows
start-ui.bat
```

To point at a specific catalog directory:

```bash
./start-ui.sh --root /path/to/integration-catalog
```

The editor opens at **http://localhost:8501**. Press **Ctrl+C** to stop.

You can also launch manually after installing the package:

```bash
integration-catalog-ui --root /path/to/integration-catalog
```

---

## Python library

The library is the foundation shared by the CLI and the web editor. Import it
to script catalog operations or build your own tooling.

### Loading and validating

```python
from integration_catalog import Catalog

catalog = Catalog.load("/path/to/integration-catalog")

errors = catalog.validate()
if errors:
    for err in errors:
        print(err)
```

### Reading data

```python
org = catalog.get_organization("nextcloud")
entry = catalog.get_entry("COMMUNITY-opendesk-collabora")
platforms = catalog.list_definitions("platforms")

# Entries support arbitrary locales; en-US and de-DE are required
print(entry.locale_codes())          # ['de-DE', 'en-US']
print(entry.en_US.name)              # convenience property
print(entry.locale("de-DE").name)    # explicit lookup
```

### Creating an organization

```python
from integration_catalog import Organization, OrganizationLocale

org = Organization(
    id="my-org",
    en_US=OrganizationLocale(name="My Org", short_description="My Org Ltd"),
    de_DE=OrganizationLocale(name="My Org", short_description="My Org GmbH"),
)
catalog.add_organization(org)  # writes organizations/org-my-org.yaml
```

### Creating an entry

```python
from integration_catalog import Entry, EntryLocale, EntryLink

entry = Entry(
    id="COMMUNITY-my-app",
    locales={
        "en-US": EntryLocale(
            name="My App",
            short_description="An example integration",
            long_description="Full **Markdown** description here.",
            links=[EntryLink(description="Homepage", url="https://example.com")],
        ),
        "de-DE": EntryLocale(
            name="Meine App",
            short_description="Eine Beispiel-Integration",
            long_description="Vollstaendige **Markdown**-Beschreibung.",
            links=[EntryLink(description="Startseite", url="https://example.com")],
        ),
    },
)
catalog.add_entry(entry)  # writes entries/COMMUNITY-my-app/COMMUNITY-my-app.yaml
```

### Key classes

| Class | Purpose |
|---|---|
| `Catalog` | Central API: load, validate, CRUD for all entity types |
| `Entry` | An integration entry with locale dict, technical and organizational specs |
| `EntryLocale` | Translatable fields: name, descriptions, keywords, links |
| `EntryLink` | A single link (description + URL) inside a locale |
| `Organization` | Vendor or support contact with en-US / de-DE locales |
| `DefinitionFile` | A collection of definition items (e.g. all artifact types) |
| `DefinitionItem` | A single definition (id + localized name/description) |
| `TechnicalSpecifications` | Capabilities, platforms, products, artifacts, protocols |
| `OrganizationalSpecifications` | Vendor, support contact, support status |

### Exception hierarchy

```
CatalogError                    Base for all catalog errors
 +-- ValidationError            Data model validation failure
 |    +-- MissingLocaleError    Required locale (en-US / de-DE) is absent
 |    +-- InvalidReferenceError Entry references a non-existent definition or org
 +-- NotFoundError              Requested element does not exist
 +-- DuplicateIdError           Element with the same ID already exists
```

---

## CLI reference

```
integration-catalog [--root PATH] <command>
```

`--root` defaults to the current working directory. Use `--help` on any
command for full option documentation.

### Validation

| Command | Description |
|---|---|
| `validate` | Check all definitions, organizations, and entries for errors |

### Definitions

| Command | Description |
|---|---|
| `definition list-types` | Show all definition types and item counts |
| `definition list <type>` | List items of a definition type |
| `definition show <type> <id>` | Show details of one item |
| `definition add <type>` | Add a new item (`--id`, `--en-name`, `--en-description`, `--de-name`, `--de-description` required) |
| `definition update <type> <id>` | Update an item (supply only the fields to change) |
| `definition remove <type> <id>` | Remove an item (`--yes` to skip confirmation) |

### Organizations

| Command | Description |
|---|---|
| `org list` | List all organizations |
| `org show <id>` | Show organization details |
| `org add` | Add a new organization (`--id`, `--en-name`, `--en-short`, `--de-name`, `--de-short` required) |
| `org update <id>` | Update an organization (supply only the fields to change) |
| `org remove <id>` | Remove an organization (`--yes` to skip confirmation) |

### Entries

| Command | Description |
|---|---|
| `entry list` | List all entries |
| `entry show <id>` | Show full entry details including all locales |
| `entry add` | Add a new entry (`--id`, `--en-name`, `--en-short`, `--en-long`, `--de-name`, `--de-short`, `--de-long` required) |
| `entry update <id>` | Update an entry (supply only the fields to change) |
| `entry remove <id>` | Remove an entry (`--yes` to skip confirmation) |

### Examples

```bash
# Validate the catalog
integration-catalog --root ../.. validate

# List all definition types
integration-catalog --root ../.. definition list-types

# Add a new platform definition
integration-catalog --root ../.. definition add platforms \
    --id Docker \
    --en-name Docker --en-description "Container-based deployments" \
    --de-name Docker --de-description "Container-basierte Installationen"

# Add a new entry with technical specs
integration-catalog --root ../.. entry add \
    --id COMMUNITY-my-app \
    --en-name "My App" --en-short "Short desc" --en-long "Full description" \
    --de-name "Meine App" --de-short "Kurzbeschreibung" --de-long "Vollstaendige Beschreibung" \
    --vendor-id community \
    --capabilities sso --platforms Kubernetes --artifacts documentation

# Show entry details
integration-catalog --root ../.. entry show COMMUNITY-my-app
```

---

## Web editor

The Streamlit-based editor provides a browser UI for visual catalog management.
See [USAGE.md](USAGE.md) for the full user guide.

### Starting

| Method | Command |
|---|---|
| Shell script (recommended) | `./start-ui.sh [--root PATH]` |
| Windows batch file | `start-ui.bat [--root PATH]` |
| Installed entry point | `integration-catalog-ui [--root PATH]` |
| Streamlit directly | `streamlit run src/integration_catalog/ui.py -- --root PATH` |

The shell scripts handle first-time setup (virtualenv, dependencies)
automatically.

### Sidebar

The sidebar shows catalog statistics, a **Reload catalog from disk** button,
and a **Git** section that displays the number of uncommitted changes with the
option to commit and push directly from the editor.

### Pages

| Page | What you can do |
|---|---|
| **Entries** | Search, create, edit and delete integration entries. Select a translation to edit its locale-specific fields (name, descriptions, keywords, links). Organizational and technical specs are shared across translations. |
| **Organizations** | Manage vendor and support contact organizations with en-US / de-DE descriptions. |
| **Definitions** | Edit the controlled vocabularies (artifacts, capabilities, platforms, products) used by entries. |
| **Validate** | Run a full consistency check and see a list of all errors. |

### Git integration

The editor automatically stages files with `git add` after every save and
`git rm` after every delete. The sidebar shows a count of uncommitted changes
and offers a **Commit changes** dialog where you enter a commit message,
review changed files, and optionally push to the remote.

---

## Catalog structure on disk

The tools expect the following directory layout at the catalog root:

```
<catalog-root>/
  definitions/
    artifacts.yaml
    capabilities.yaml
    platforms.yaml
    univention_products.yaml
  organizations/
    org-<id>.yaml
  entries/
    <category>/
      <ENTRY-ID>/
        <ENTRY-ID>.yaml
        logo.svg          # optional
        logo.svg.license  # REUSE sidecar for the logo
```

All YAML files carry an SPDX license header. Binary assets (logos, images)
use `.license` sidecar files for REUSE compliance.

---

## Validation rules

1. Every organization and entry must have both `en-US` and `de-DE` locales.
2. Organization IDs must consist of letters, digits, hyphens and underscores.
3. `name`, `short_description`, and (for entries) `long_description` must be
   non-empty.
4. Markdown fields must not contain control characters or unclosed HTML tags.
5. `vendor_id` and `support_contact_id` in entries must reference existing
   organization IDs (or be empty).
6. `capabilities` and `artifacts` references are checked case-insensitively
   against their definition files.
7. `compatible_platforms` and `compatible_products` references are checked
   case-sensitively.
8. Removing an organization or definition item that is still referenced by an
   entry is blocked with an `InvalidReferenceError`.

---

## Contributing

### Repository layout

```
editor/integration_catalog/
  pyproject.toml          # package metadata, dependencies, entry points
  start-ui.sh             # Linux/macOS launcher
  start-ui.bat            # Windows launcher
  src/
    integration_catalog/
      __init__.py          # public API exports
      models.py            # dataclass models (Entry, Organization, ...)
      catalog.py           # Catalog class: loading, validation, CRUD
      cli.py               # Click CLI (integration-catalog command)
      ui.py                # Streamlit web editor (integration-catalog-ui)
      io.py                # YAML load/save helpers
      exceptions.py        # exception hierarchy
```

### Setting up a development environment

```bash
cd editor/integration_catalog
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # installs pytest, pytest-cov as well
```

### Architecture overview

The codebase follows a layered design:

```
ui.py / cli.py          UI layer (Streamlit / Click)
       |
    catalog.py           Business logic and orchestration
       |
    models.py            Data classes with validate / to_dict / from_dict
       |
    io.py                YAML serialization
```

- **`models.py`** defines all data structures as Python `dataclass` objects.
  Each model has `validate()`, `to_dict()`, and `from_dict()` methods. The
  `Entry` class uses a `locales: dict[str, EntryLocale]` mapping to support
  an arbitrary number of translations beyond the two required ones.

- **`catalog.py`** contains the `Catalog` class which loads the full catalog
  from disk, provides CRUD methods for every entity type, runs validation,
  and automatically stages changes in git. All write operations persist to
  disk immediately.

- **`cli.py`** is a Click application that exposes every `Catalog` method as
  a terminal command. Output is formatted with Rich tables.

- **`ui.py`** is a Streamlit application. It caches the `Catalog` instance in
  session state and re-renders on every interaction. The UI uses Streamlit
  forms for atomic edits and session state for multi-step flows (e.g. the
  delete confirmation dialog and the git commit dialog).

- **`io.py`** handles YAML reading and writing, including the SPDX license
  header and literal-block formatting for multi-line strings.

### Adding a new field to an entry

1. Add the field to the relevant dataclass in `models.py`.
2. Update `to_dict()` and `from_dict()` on that class.
3. Update `validate()` if the field needs validation.
4. Add a widget for the field in `_entry_edit_form()` and `_entries_add()` in
   `ui.py`.
5. Update the save logic in both forms to include the new field.
6. Add CLI options in `cli.py` (`entry add` and `entry update`).
7. If the field references definition IDs, add a check in
   `Catalog._validate_entry_references()`.

### Running tests

```bash
pytest
```

Test configuration is in `pyproject.toml` (`testpaths = ["tests"]`).

### Code style

- All source files start with an SPDX license header.
- Type annotations are used throughout (`from __future__ import annotations`).
- Models use `@dataclass` with explicit `field(default_factory=...)` for
  mutable defaults.

---

## License

AGPL-3.0-only. See `LICENSES/AGPL-3.0-only.txt` in the repository root.
