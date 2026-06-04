---
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: AGPL-3.0-only
SPDX-FileCopyrightText: 2026 Univention GmbH
---

# Integration Catalog Editor -- User Guide

The Integration Catalog Editor is a browser-based tool for managing the
Univention Integration Catalog. It lets you create, view, edit, and delete
**definitions**, **organizations**, and **integration entries** without
needing to edit YAML files by hand.

---

## Starting the editor

### Linux / macOS

Open a terminal, navigate to the `editor/integration_catalog/` directory,
and run:

```bash
./start-ui.sh
```

The script automatically:
1. Creates a Python virtual environment (first run only, takes ~1 minute)
2. Installs all required packages (first run only)
3. Opens the editor in your default web browser at **http://localhost:8501**

To use a specific catalog directory:

```bash
./start-ui.sh --root /path/to/integration-catalog
```

### Windows

Double-click `start-ui.bat`, or open a Command Prompt and run:

```
start-ui.bat
```

With a custom catalog path:

```
start-ui.bat --root C:\path\to\integration-catalog
```

### Stopping the editor

Press **Ctrl+C** in the terminal window where you started the script.

---

## Requirements

- **Python 3.11 or later** must be installed and available as `python3`
  (Linux/macOS) or `python` (Windows).
- An internet connection is needed on the first run to download packages.
- No other software installation is required.

---

## Navigation

The editor has four sections, accessible from the **left sidebar**:

| Section | Purpose |
|---|---|
| 📦 Entries | Manage integration entries |
| 🏢 Organizations | Manage vendor and support contact organizations |
| 📐 Definitions | Manage controlled vocabularies (artifact types, capabilities, platforms, products) |
| ✅ Validate | Check the catalog for errors |

Use the **Reload catalog from disk** button in the sidebar at any time to
refresh the editor if YAML files were changed externally.

---

## Working with Organizations

Organizations represent vendors and support contacts that can be assigned to
entries. Each organization has an English and a German description.

### Viewing and editing

1. Use the search box to filter by ID or name.
2. Expand an organization to edit its fields.
3. Click **Save changes**.

### Adding a new organization

1. Click **Add new**.
2. Enter a unique ID (letters, digits, hyphens and underscores only).
3. Fill in the English and German name, short description, website, contact
   email and logo filename.
4. Click **Add organization**.

### Deleting an organization

1. Expand the organization.
2. Click **Delete**.
3. A confirmation checkbox appears. Check it, then click **Confirm**.

> Deletion is blocked if any entry references the organization as vendor or
> support contact. Update those entries first.

---

## Working with Entries

Integration entries are the main content of the catalog. Each entry describes
one application or service integration with Univention products.

### Translations

Each entry supports multiple translations. The required locales are **en-US**
and **de-DE**; additional locales can be added freely.

- Use the **Select translation to edit** dropdown to switch between locales.
- Enter a locale code (e.g. `fr-FR`) in the text field and click **Add** to
  create a new translation.

The locale-specific fields (name, descriptions, keywords, links) change when
you switch the selected translation. The organizational and technical
specifications below are shared across all translations.

### Viewing and editing

1. Use the search box to find an entry by ID or name.
2. Expand the entry.
3. Select the translation you want to edit from the dropdown.
4. Edit the locale-specific fields:
   - **Name, Short description, Long description** -- the long description
     supports full Markdown (headings, lists, bold, links, code blocks)
   - **Keywords** -- comma-separated
   - **Links** -- each link has a Description and a URL. Existing links can
     be edited inline; add a new link by filling the empty row at the bottom.
5. Edit the shared fields below the divider:
   - **Vendor / Support contact** -- select from the dropdown of known
     organizations
   - **Capabilities, Artifacts, Products, Platforms** -- multi-select from
     defined values
   - **Protocols** -- free text, comma-separated (e.g. `OIDC, SAML`)
   - **Version** -- free text
6. Click **Save changes**.

### Adding a new entry

1. Click **Add new**.
2. Enter a unique Entry ID (e.g. `COMMUNITY-my-app`).
3. Optionally add additional translations using the locale code input at the
   top.
4. Fill in the locale-specific fields for each translation.
5. Fill in the organizational and technical specifications.
6. Click **Add entry**.

### Deleting an entry

1. Expand the entry.
2. Click **Delete** below the form.
3. A confirmation checkbox appears. Check it, then click **Confirm**.
4. Click **Cancel** to abort.

---

## Working with Definitions

Definitions are the controlled vocabulary used across entries. Definitions should
only be added by Univention. There are four types:

- **Artifacts** -- how an integration is delivered (e.g. documentation, packaged integration)
- **Capabilities** -- what the integration supports (e.g. Single Sign-On)
- **Platforms** -- which deployment platforms are supported (e.g. UCS, Kubernetes)
- **Univention Products** -- which Univention products are compatible (e.g. Nubus, UCS@school)

### Viewing and editing

1. Select a definition type from the dropdown.
2. Each item appears as a collapsible row. Click it to expand.
3. Edit the English and German name and description fields.
4. Click **Save changes** to write the updated YAML file.

### Adding a new definition item

1. Click the **Add new** tab.
2. Fill in the ID (must be unique within the type) and both English and
   German fields.
3. Click **Add**.

### Deleting a definition item

1. Expand the item in the list.
2. Click **Delete**.
3. A confirmation checkbox appears. Check it, then click **Confirm**.
4. Click **Cancel** to abort.

> **Note:** Deletion is blocked if any entry still references the item.
> Remove the reference from entries first.

---

## Validation

Click **Run validation** on the Validate page to check the entire catalog
for:

- Missing English or German descriptions
- References to organizations that do not exist
- References to capabilities, artifacts, platforms or products not defined in
  the definition files
- Markdown content with illegal characters or unclosed HTML tags

Any errors are listed with a description of what needs to be fixed.

---

## Git integration

The editor integrates with Git to help you track and commit your changes.

### Automatic staging

Every time you save or delete an entry, organization, or definition, the
editor automatically runs `git add` (or `git rm` for deletions) so the
changed file is staged. You do not need to stage files manually.

### Committing changes

The sidebar shows the number of files with uncommitted changes. Click
**Commit changes** to open the commit dialog:

1. Review the list of changed files and the diff summary.
2. Enter a **commit message** (required).
3. Optionally check **Push after commit** to push to the remote immediately.
4. Click **Commit** to proceed, or **Cancel** to close the dialog.

If the catalog root is not inside a Git repository, the Git section is
hidden.

---

## How changes are saved

All changes are written **immediately to disk** as YAML files when you click
Save or Add. There is no separate "publish" step. The files are written with
an SPDX license header and proper YAML formatting.

- Organizations are saved in `organizations/org-<id>.yaml`
- Entries are saved in `entries/<entry-id>/<entry-id>.yaml`
- Definition files are updated in `definitions/`
