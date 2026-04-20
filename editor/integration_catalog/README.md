# integration-catalog

Python library and CLI tool for managing the Univention Integration Catalog.

## Installation

```bash
cd tools/integration_catalog
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Library usage

```python
from integration_catalog import Catalog, Organization, OrganizationLocale, OrgMetadata

# Load the catalog
catalog = Catalog.load("/path/to/integration-catalog")

# Validate everything
errors = catalog.validate()

# Read
org = catalog.get_organization("nextcloud")
entry = catalog.get_entry("UCSAPP-nextcloud")
artifacts = catalog.list_definitions("artifacts")

# Add a new organization
from integration_catalog import Organization, OrganizationLocale
org = Organization(
    id="my-org",
    en_US=OrganizationLocale(name="My Org", short_description="My Org Ltd"),
    de_DE=OrganizationLocale(name="My Org", short_description="My Org GmbH"),
)
catalog.add_organization(org)  # writes org-my-org.yaml immediately

# Add a new entry
from integration_catalog import Entry, EntryLocale
entry = Entry(
    id="COMMUNITY-my-app",
    en_US=EntryLocale(name="My App", short_description="My App", long_description="..."),
    de_DE=EntryLocale(name="Meine App", short_description="Meine App", long_description="..."),
)
catalog.add_entry(entry)  # writes to entries/COMMUNITY-my-app/COMMUNITY-my-app.yaml
```

## CLI usage

```
integration-catalog --root /path/to/catalog <command>
```

### Commands

| Command | Description |
|---|---|
| `validate` | Validate the entire catalog |
| `definition list-types` | List definition types |
| `definition list <type>` | List items of a definition type |
| `definition show <type> <id>` | Show a definition item |
| `definition add <type>` | Add a new definition item |
| `definition update <type> <id>` | Update a definition item |
| `definition remove <type> <id>` | Remove a definition item |
| `org list` | List all organizations |
| `org show <id>` | Show an organization |
| `org add` | Add a new organization |
| `org update <id>` | Update an organization |
| `org remove <id>` | Remove an organization |
| `entry list` | List all entries |
| `entry show <id>` | Show an entry |
| `entry add` | Add a new entry |
| `entry update <id>` | Update an entry |
| `entry remove <id>` | Remove an entry |

Use `--help` on any command for full option documentation.

## Validation rules

- Every organization and entry must have both `en-US` and `de-DE` locale blocks.
- `vendor_id` and `support_contact_id` in entries must reference existing organization IDs (or be empty).
- `capabilities`, `artifacts`, `compatible_platforms`, and `compatible_products` in entries must reference IDs defined in the corresponding definition YAML files.
- Removing an organization or definition item that is still referenced by an entry raises `InvalidReferenceError`.
