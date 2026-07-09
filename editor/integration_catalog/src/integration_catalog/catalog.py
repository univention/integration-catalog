# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""
Catalog: the central object that loads, validates, and manages the entire
integration catalog on disk.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

from .exceptions import (
    CatalogError,
    DuplicateIdError,
    InvalidReferenceError,
    NotFoundError,
    ValidationError,
)
from .io import load_yaml, save_yaml
from .models import (
    DefinitionFile,
    DefinitionItem,
    Entry,
    EntryMetadata,
    LocalizedText,
    Organization,
    OrganizationLocale,
    OrgMetadata,
    _today_str,
)

# Mapping from definition YAML filename → list key inside the file
_DEFINITION_FILES: dict[str, str] = {
    "artifacts.yaml": "artifacts",
    "capabilities.yaml": "capabilities",
    "platforms.yaml": "platforms",
    "univention_products.yaml": "univention_products",
    # technology.yaml has incomplete data (missing IDs) — loaded read-only
    "technology.yaml": "platforms",
}

# Definition files whose IDs can be referenced from entries
_REFERABLE_DEFINITIONS = {
    "artifacts",
    "capabilities",
    "platforms",
    "univention_products",
}


class Catalog:
    """
    Represents the full integration catalog rooted at *root_path*.

    Attributes
    ----------
    root_path : Path
        Absolute path to the top-level catalog directory.
    definitions : dict[str, DefinitionFile]
        Keyed by list_key (e.g. ``'artifacts'``, ``'capabilities'``, …).
    organizations : dict[str, Organization]
        Keyed by organization id.
    entries : dict[str, Entry]
        Keyed by entry id.
    """

    def __init__(self, root_path: Path | str) -> None:
        self.root_path = Path(root_path).resolve()
        self.definitions: dict[str, DefinitionFile] = {}
        self.organizations: dict[str, Organization] = {}
        self.entries: dict[str, Entry] = {}

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _git_track(self, path: Path) -> None:
        """Run ``git add <path>`` so new or modified files are staged.

        Silently does nothing if the catalog is not inside a git repository.
        """
        try:
            subprocess.run(
                ["git", "add", "--", str(path)],
                cwd=self.root_path,
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            _log.debug("git add %s failed: %s", path, exc)

    def _git_rm(self, path: Path) -> None:
        """Run ``git rm --cached <path>`` so deleted files are staged for removal.

        Silently does nothing if the catalog is not inside a git repository.
        """
        try:
            subprocess.run(
                ["git", "rm", "--cached", "--", str(path)],
                cwd=self.root_path,
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            _log.debug("git rm %s failed: %s", path, exc)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, root_path: Path | str) -> "Catalog":
        """Load the entire catalog from *root_path* and return a Catalog instance."""
        catalog = cls(root_path)
        catalog._load_definitions()
        catalog._load_organizations()
        catalog._load_entries()
        return catalog

    def _load_definitions(self) -> None:
        defs_dir = self.root_path / "definitions"
        if not defs_dir.is_dir():
            raise CatalogError(f"definitions directory not found: {defs_dir}")
        for filename, list_key in _DEFINITION_FILES.items():
            path = defs_dir / filename
            if not path.exists():
                continue
            data = load_yaml(path)
            df = DefinitionFile.from_dict(data, list_key=list_key, path=path)
            # technology.yaml reuses list_key 'platforms' → store under 'technology'
            store_key = "technology" if filename == "technology.yaml" else list_key
            self.definitions[store_key] = df

    def _load_organizations(self) -> None:
        orgs_dir = self.root_path / "organizations"
        if not orgs_dir.is_dir():
            return
        for path in sorted(orgs_dir.glob("org-*.yaml")):
            data = load_yaml(path)
            org = Organization.from_dict(data, path=path)
            if org.id:
                self.organizations[org.id] = org

    def _load_entries(self) -> None:
        entries_dir = self.root_path / "entries"
        if not entries_dir.is_dir():
            return
        # Recursively find all YAML files two levels deep (collection/entry-dir/entry.yaml)
        for yaml_path in sorted(entries_dir.rglob("*.yaml")):
            # skip editor backup files
            if yaml_path.suffix != ".yaml":
                continue
            data = load_yaml(yaml_path)
            if "id" not in data and "description" not in data:
                continue  # not an entry file
            entry = Entry.from_dict(data, path=yaml_path)
            if entry.id:
                self.entries[entry.id] = entry

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """
        Validate the entire catalog.

        Returns a list of human-readable error strings. An empty list means
        the catalog is valid.
        """
        errors: list[str] = []

        # Validate organizations
        for org_id, org in self.organizations.items():
            try:
                org.validate()
            except ValidationError as exc:
                errors.append(f"Organization '{org_id}': {exc}")

        # Validate entries and their references
        known_org_ids = set(self.organizations.keys())
        known_entry_ids = set(self.entries.keys())
        known_capability_ids = {
            item.id.lower()
            for item in self.definitions.get("capabilities", DefinitionFile("capabilities")).items
        }
        known_artifact_ids = {
            item.id.lower()
            for item in self.definitions.get("artifacts", DefinitionFile("artifacts")).items
        }
        known_platform_ids = {
            item.id
            for item in self.definitions.get("platforms", DefinitionFile("platforms")).items
        }
        known_product_ids = {
            item.id
            for item in self.definitions.get("univention_products", DefinitionFile("univention_products")).items
        }
        known_technology_ids = {
            item.id
            for item in self.definitions.get("technology", DefinitionFile("technology")).items
        }

        for entry_id, entry in self.entries.items():
            try:
                entry.validate()
            except ValidationError as exc:
                errors.append(f"Entry '{entry_id}': {exc}")
                continue

            org_spec = entry.organizational_specifications
            tech_spec = entry.technical_specifications

            # Check vendor_id reference
            if org_spec.vendor_id and org_spec.vendor_id not in known_org_ids:
                errors.append(
                    f"Entry '{entry_id}': vendor_id '{org_spec.vendor_id}' "
                    f"does not match any known organization."
                )

            # Check support_contact_id reference
            if org_spec.support_contact_id and org_spec.support_contact_id not in known_org_ids:
                errors.append(
                    f"Entry '{entry_id}': support_contact_id '{org_spec.support_contact_id}' "
                    f"does not match any known organization."
                )

            # Check capabilities references (case-insensitive)
            for cap in tech_spec.capabilities:
                if cap.lower() not in known_capability_ids:
                    errors.append(
                        f"Entry '{entry_id}': capability '{cap}' "
                        f"is not defined in capabilities.yaml."
                    )

            # Check artifact references
            for art in tech_spec.artifacts:
                if art.lower() not in known_artifact_ids:
                    errors.append(
                        f"Entry '{entry_id}': artifact '{art}' "
                        f"is not defined in artifacts.yaml."
                    )

            # Check compatible_platforms references
            for plat in tech_spec.compatible_platforms:
                if plat not in known_platform_ids:
                    errors.append(
                        f"Entry '{entry_id}': compatible_platform '{plat}' "
                        f"is not defined in platforms.yaml."
                    )

            # Check compatible_products references
            for prod in tech_spec.compatible_products:
                if prod not in known_product_ids:
                    errors.append(
                        f"Entry '{entry_id}': compatible_product '{prod}' "
                        f"is not defined in univention_products.yaml."
                    )

            # Check protocols references (technology)
            for tech in tech_spec.protocols:
                if tech not in known_technology_ids:
                    errors.append(
                        f"Entry '{entry_id}': protocol '{tech}' "
                        f"is not defined in technology.yaml."
                    )

            # Check dependency references (other entries)
            for dep in tech_spec.dependencies:
                if dep not in known_entry_ids:
                    errors.append(
                        f"Entry '{entry_id}': dependency '{dep}' "
                        f"does not match any known entry."
                    )

        return errors

    # ------------------------------------------------------------------
    # Definition CRUD
    # ------------------------------------------------------------------

    def list_definitions(self, definition_type: str) -> list[DefinitionItem]:
        """Return all items of a definition type (e.g. 'artifacts', 'capabilities')."""
        df = self._get_definition_file(definition_type)
        return list(df.items)

    def get_definition(self, definition_type: str, item_id: str) -> DefinitionItem:
        df = self._get_definition_file(definition_type)
        item = df.get(item_id)
        if item is None:
            raise NotFoundError(f"Definition '{item_id}' not found in '{definition_type}'.")
        return item

    def add_definition(self, definition_type: str, item: DefinitionItem) -> None:
        """Add a new definition item and persist to disk."""
        df = self._get_definition_file(definition_type)
        df.add(item)  # raises DuplicateIdError / ValidationError
        if df.path:
            self._save_definition_file(df)

    def update_definition(self, definition_type: str, item: DefinitionItem) -> None:
        """Update an existing definition item and persist to disk."""
        df = self._get_definition_file(definition_type)
        df.update(item)  # raises NotFoundError / ValidationError
        if df.path:
            self._save_definition_file(df)

    def remove_definition(self, definition_type: str, item_id: str) -> None:
        """Remove a definition item and persist to disk."""
        # Safety: check that no entry references this id
        self._check_definition_not_referenced(definition_type, item_id)
        df = self._get_definition_file(definition_type)
        df.remove(item_id)
        if df.path:
            self._save_definition_file(df)

    def _get_definition_file(self, definition_type: str) -> DefinitionFile:
        df = self.definitions.get(definition_type)
        if df is None:
            raise NotFoundError(
                f"Definition type '{definition_type}' not found. "
                f"Known types: {sorted(self.definitions.keys())}"
            )
        return df

    def _save_definition_file(self, df: DefinitionFile) -> None:
        assert df.path is not None
        data = df.to_dict()
        save_yaml(df.path, data)
        self._git_track(df.path)

    def _check_definition_not_referenced(self, definition_type: str, item_id: str) -> None:
        """Raise InvalidReferenceError if any entry references item_id in definition_type."""
        for entry_id, entry in self.entries.items():
            ts = entry.technical_specifications
            refs: list[str] = []
            if definition_type == "artifacts":
                refs = ts.artifacts
            elif definition_type == "capabilities":
                refs = ts.capabilities
            elif definition_type == "platforms":
                refs = ts.compatible_platforms
            elif definition_type == "univention_products":
                refs = ts.compatible_products
            elif definition_type == "technology":
                refs = ts.protocols
            if item_id in refs or item_id.lower() in [r.lower() for r in refs]:
                raise InvalidReferenceError(
                    f"Cannot remove definition '{item_id}' from '{definition_type}': "
                    f"entry '{entry_id}' still references it."
                )

    # ------------------------------------------------------------------
    # Organization CRUD
    # ------------------------------------------------------------------

    def list_organizations(self) -> list[Organization]:
        return list(self.organizations.values())

    def get_organization(self, org_id: str) -> Organization:
        org = self.organizations.get(org_id)
        if org is None:
            raise NotFoundError(f"Organization '{org_id}' not found.")
        return org

    def add_organization(self, org: Organization) -> None:
        """Add a new organization, validate it, write the YAML file."""
        org.validate()
        if org.id in self.organizations:
            raise DuplicateIdError(f"Organization '{org.id}' already exists.")
        org.metadata.last_updated = _today_str()
        org.path = self.root_path / "organizations" / f"org-{org.id}.yaml"
        self.organizations[org.id] = org
        self._save_organization(org)

    def update_organization(self, org: Organization) -> None:
        """Update an existing organization and persist to disk."""
        if org.id not in self.organizations:
            raise NotFoundError(f"Organization '{org.id}' not found.")
        org.validate()
        existing = self.organizations[org.id]
        org.path = existing.path
        org.metadata.last_updated = _today_str()
        self.organizations[org.id] = org
        self._save_organization(org)

    def remove_organization(self, org_id: str) -> None:
        """Remove an organization; raises if any entry still references it."""
        if org_id not in self.organizations:
            raise NotFoundError(f"Organization '{org_id}' not found.")
        # Check no entry references this org
        for entry_id, entry in self.entries.items():
            os = entry.organizational_specifications
            if os.vendor_id == org_id or os.support_contact_id == org_id:
                raise InvalidReferenceError(
                    f"Cannot remove organization '{org_id}': "
                    f"entry '{entry_id}' still references it."
                )
        org = self.organizations.pop(org_id)
        if org.path and org.path.exists():
            org.path.unlink()
            self._git_rm(org.path)

    def _save_organization(self, org: Organization) -> None:
        assert org.path is not None
        comment = f"# Organization definition to be linked in an integration entry as vendor of the integration or the integrated application.\n\n# Description of organization \"{org.en_US.name}\"."
        save_yaml(org.path, org.to_dict(), header_comment=comment)
        self._git_track(org.path)

    # ------------------------------------------------------------------
    # Entry CRUD
    # ------------------------------------------------------------------

    def list_entries(self) -> list[Entry]:
        """Return all entries."""
        return list(self.entries.values())

    def get_entry(self, entry_id: str) -> Entry:
        entry = self.entries.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Entry '{entry_id}' not found.")
        return entry

    def add_entry(self, entry: Entry) -> None:
        """
        Add a new entry.

        The entry is written to entries/<entry.id>/<entry.id>.yaml.
        """
        entry.validate()
        self._validate_entry_references(entry)
        if entry.id in self.entries:
            raise DuplicateIdError(f"Entry '{entry.id}' already exists.")
        entry.metadata.last_update_date = _today_str()
        entry_dir = self.root_path / "entries" / entry.id
        entry.path = entry_dir / f"{entry.id}.yaml"
        self.entries[entry.id] = entry
        self._save_entry(entry)

    def update_entry(self, entry: Entry) -> None:
        """Update an existing entry and persist to disk."""
        if entry.id not in self.entries:
            raise NotFoundError(f"Entry '{entry.id}' not found.")
        entry.validate()
        self._validate_entry_references(entry)
        existing = self.entries[entry.id]
        entry.path = existing.path
        entry.metadata.last_update_date = _today_str()
        self.entries[entry.id] = entry
        self._save_entry(entry)

    def remove_entry(self, entry_id: str) -> None:
        """Remove an entry YAML file (leaves any sibling assets in place)."""
        if entry_id not in self.entries:
            raise NotFoundError(f"Entry '{entry_id}' not found.")
        entry = self.entries.pop(entry_id)
        if entry.path and entry.path.exists():
            entry.path.unlink()
            self._git_rm(entry.path)

    def _save_entry(self, entry: Entry) -> None:
        assert entry.path is not None
        save_yaml(entry.path, entry.to_dict())
        self._git_track(entry.path)

    def _validate_entry_references(self, entry: Entry) -> None:
        """Raise InvalidReferenceError if entry references unknown IDs."""
        errors: list[str] = []
        known_org_ids = set(self.organizations.keys())
        os = entry.organizational_specifications
        ts = entry.technical_specifications

        if os.vendor_id and os.vendor_id not in known_org_ids:
            errors.append(f"vendor_id '{os.vendor_id}' does not match any known organization.")
        if os.support_contact_id and os.support_contact_id not in known_org_ids:
            errors.append(f"support_contact_id '{os.support_contact_id}' does not match any known organization.")

        known_caps = {
            item.id.lower()
            for item in self.definitions.get("capabilities", DefinitionFile("capabilities")).items
        }
        for cap in ts.capabilities:
            if cap.lower() not in known_caps:
                errors.append(f"capability '{cap}' is not defined in capabilities.yaml.")

        known_arts = {
            item.id.lower()
            for item in self.definitions.get("artifacts", DefinitionFile("artifacts")).items
        }
        for art in ts.artifacts:
            if art.lower() not in known_arts:
                errors.append(f"artifact '{art}' is not defined in artifacts.yaml.")

        known_plats = {
            item.id
            for item in self.definitions.get("platforms", DefinitionFile("platforms")).items
        }
        for plat in ts.compatible_platforms:
            if plat not in known_plats:
                errors.append(f"compatible_platform '{plat}' is not defined in platforms.yaml.")

        known_prods = {
            item.id
            for item in self.definitions.get("univention_products", DefinitionFile("univention_products")).items
        }
        for prod in ts.compatible_products:
            if prod not in known_prods:
                errors.append(f"compatible_product '{prod}' is not defined in univention_products.yaml.")

        known_techs = {
            item.id
            for item in self.definitions.get("technology", DefinitionFile("technology")).items
        }
        for tech in ts.protocols:
            if tech not in known_techs:
                errors.append(f"protocol '{tech}' is not defined in technology.yaml.")

        if errors:
            raise InvalidReferenceError(
                f"Entry '{entry.id}' has invalid references:\n  " + "\n  ".join(errors)
            )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def definition_types(self) -> list[str]:
        """Return all loaded definition type keys."""
        return sorted(self.definitions.keys())
