# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""Data models for all YAML files in the integration catalog."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from .exceptions import MissingLocaleError, ValidationError

REQUIRED_LOCALES = ("en-US", "de-DE")
SCHEMA_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Markdown validation
# ---------------------------------------------------------------------------

# Regex for detecting unclosed or malformed HTML tags embedded in markdown.
# CommonMark allows inline HTML, but unclosed block-level tags produce broken
# output in every major renderer.
_UNCLOSED_HTML_TAG_RE = re.compile(
    r"<(?P<tag>[a-zA-Z][a-zA-Z0-9]*)(?:\s[^>]*)?>(?!.*</(?P=tag)\s*>)",
    re.DOTALL,
)

# Characters that are illegal in text content and break all markdown parsers.
_ILLEGAL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_markdown(text: str, field_name: str) -> None:
    """
    Raise ValidationError if *text* contains content that would produce
    broken output when parsed by a standard markdown parser.

    Checks performed:
    - No control characters (except tab, newline, carriage return).
    - No unclosed inline HTML tags (which produce malformed HTML output).
    """
    if _ILLEGAL_CHARS_RE.search(text):
        raise ValidationError(
            f"{field_name}: contains illegal control characters that break markdown parsers."
        )
    match = _UNCLOSED_HTML_TAG_RE.search(text)
    if match:
        raise ValidationError(
            f"{field_name}: contains unclosed HTML tag '<{match.group('tag')}>' "
            f"which produces malformed output in markdown renderers."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_locales(obj: object, field_name: str) -> None:
    """Raise MissingLocaleError if obj is missing en-US or de-DE attributes."""
    for locale in REQUIRED_LOCALES:
        attr = locale.replace("-", "_")
        val = getattr(obj, attr, None)
        if val is None:
            raise MissingLocaleError(
                f"{obj.__class__.__name__}.{field_name}: locale '{locale}' is required."
            )


def _today_str() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Shared primitive
# ---------------------------------------------------------------------------

@dataclass
class LocalizedText:
    """A simple name/description pair for one locale."""
    name: str
    description: str

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("LocalizedText.name must not be empty.")
        if not self.description.strip():
            raise ValidationError("LocalizedText.description must not be empty.")

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "LocalizedText":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
        )


# ---------------------------------------------------------------------------
# Definition files
# ---------------------------------------------------------------------------

@dataclass
class DefinitionItem:
    """A single item inside a definition list (capability, artifact, platform, product…)."""
    id: str
    en_US: LocalizedText
    de_DE: LocalizedText

    def validate(self) -> None:
        if not self.id.strip():
            raise ValidationError("DefinitionItem.id must not be empty.")
        self.en_US.validate()
        self.de_DE.validate()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "en-US": self.en_US.to_dict(),
            "de-DE": self.de_DE.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DefinitionItem":
        return cls(
            id=data.get("id", ""),
            en_US=LocalizedText.from_dict(data.get("en-US", {})),
            de_DE=LocalizedText.from_dict(data.get("de-DE", {})),
        )


@dataclass
class DefinitionFileMetadata:
    schema_version: str = SCHEMA_VERSION
    last_updated: str = field(default_factory=_today_str)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DefinitionFileMetadata":
        return cls(
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            last_updated=str(data.get("last_updated", _today_str())),
        )


@dataclass
class DefinitionFile:
    """
    Represents one definitions YAML file (artifacts, capabilities, platforms,
    univention_products).

    The ``list_key`` is the YAML key that holds the list of items
    (e.g. 'artifacts', 'capabilities', 'platforms', 'univention_products').
    """
    list_key: str
    items: list[DefinitionItem] = field(default_factory=list)
    metadata: DefinitionFileMetadata = field(default_factory=DefinitionFileMetadata)
    # path is set by the loader; not serialised
    path: Optional[Path] = field(default=None, repr=False, compare=False)

    # ---- helpers ----------------------------------------------------------

    def get(self, item_id: str) -> Optional[DefinitionItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def ids(self) -> list[str]:
        return [item.id for item in self.items]

    def add(self, item: DefinitionItem) -> None:
        from .exceptions import DuplicateIdError
        if self.get(item.id) is not None:
            raise DuplicateIdError(
                f"A definition item with id '{item.id}' already exists in '{self.list_key}'."
            )
        item.validate()
        self.metadata.last_updated = _today_str()
        self.items.append(item)

    def update(self, item: DefinitionItem) -> None:
        from .exceptions import NotFoundError
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                item.validate()
                self.items[i] = item
                self.metadata.last_updated = _today_str()
                return
        raise NotFoundError(f"Definition item '{item.id}' not found in '{self.list_key}'.")

    def remove(self, item_id: str) -> None:
        from .exceptions import NotFoundError
        for i, existing in enumerate(self.items):
            if existing.id == item_id:
                del self.items[i]
                self.metadata.last_updated = _today_str()
                return
        raise NotFoundError(f"Definition item '{item_id}' not found in '{self.list_key}'.")

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            self.list_key: [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict, list_key: str, path: Optional[Path] = None) -> "DefinitionFile":
        metadata = DefinitionFileMetadata.from_dict(data.get("metadata", {}))
        raw_items = data.get(list_key, []) or []
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get("id", "")
            en = raw.get("en-US") or {}
            de = raw.get("de-DE") or {}
            if not item_id:
                continue
            items.append(DefinitionItem(
                id=item_id,
                en_US=LocalizedText.from_dict(en),
                de_DE=LocalizedText.from_dict(de),
            ))
        return cls(list_key=list_key, items=items, metadata=metadata, path=path)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

@dataclass
class OrganizationLocale:
    """Locale-specific attributes of an organization."""
    name: str
    short_description: str
    link: str = ""
    contact: str = ""
    logo: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("OrganizationLocale.name must not be empty.")
        if not self.short_description.strip():
            raise ValidationError("OrganizationLocale.short_description must not be empty.")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "short_description": self.short_description,
            "link": self.link,
            "contact": self.contact,
            "logo": self.logo,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrganizationLocale":
        return cls(
            name=str(data.get("name", "") or ""),
            short_description=str(data.get("short_description", "") or ""),
            link=str(data.get("link", "") or ""),
            contact=str(data.get("contact", "") or ""),
            logo=str(data.get("logo", "") or ""),
        )


@dataclass
class OrgMetadata:
    schema_version: str = SCHEMA_VERSION
    last_updated: str = field(default_factory=_today_str)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrgMetadata":
        return cls(
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            last_updated=str(data.get("last_updated", _today_str())),
        )


@dataclass
class Organization:
    """Represents a single organization YAML file."""
    id: str
    en_US: OrganizationLocale
    de_DE: OrganizationLocale
    metadata: OrgMetadata = field(default_factory=OrgMetadata)
    # path set by loader; not serialised
    path: Optional[Path] = field(default=None, repr=False, compare=False)

    def validate(self) -> None:
        if not self.id.strip():
            raise ValidationError("Organization.id must not be empty.")
        if not re.match(r'^[a-zA-Z0-9_\-]+$', self.id):
            raise ValidationError(
                f"Organization.id '{self.id}' must only contain letters, digits, hyphens and underscores."
            )
        self.en_US.validate()
        self.de_DE.validate()

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "id": self.id,
            "en-US": self.en_US.to_dict(),
            "de-DE": self.de_DE.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, path: Optional[Path] = None) -> "Organization":
        return cls(
            id=str(data.get("id", "") or ""),
            en_US=OrganizationLocale.from_dict(data.get("en-US") or {}),
            de_DE=OrganizationLocale.from_dict(data.get("de-DE") or {}),
            metadata=OrgMetadata.from_dict(data.get("metadata") or {}),
            path=path,
        )


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

@dataclass
class EntryLink:
    description: str
    url: str

    def to_dict(self) -> dict:
        return {"Description": self.description, "URL": self.url}

    @classmethod
    def from_dict(cls, data: dict) -> "EntryLink":
        return cls(
            description=str(data.get("Description", "") or ""),
            url=str(data.get("URL", "") or ""),
        )


@dataclass
class EntryLocale:
    """Locale-specific description block inside an entry."""
    name: str
    short_description: str
    long_description: str
    icon: str = ""
    keywords: list[str] = field(default_factory=list)
    links: list[EntryLink] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    visuals: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("EntryLocale.name must not be empty.")
        if not self.short_description.strip():
            raise ValidationError("EntryLocale.short_description must not be empty.")
        if not self.long_description.strip():
            raise ValidationError("EntryLocale.long_description must not be empty.")
        validate_markdown(self.short_description, "EntryLocale.short_description")
        validate_markdown(self.long_description, "EntryLocale.long_description")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "icon": self.icon,
            "keywords": [k for k in self.keywords if k],
            "links": [lnk.to_dict() for lnk in self.links],
            "tags": self.tags,
            "visuals": self.visuals,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EntryLocale":
        raw_links = data.get("links") or []
        links = [
            EntryLink.from_dict(lnk)
            for lnk in raw_links
            if isinstance(lnk, dict)
        ]
        raw_keywords = data.get("keywords") or []
        keywords = [str(k) for k in raw_keywords if k]
        return cls(
            name=str(data.get("name", "") or ""),
            short_description=str(data.get("short_description", "") or "").strip(),
            long_description=str(data.get("long_description", "") or "").strip(),
            icon=str(data.get("icon", "") or ""),
            keywords=keywords,
            links=links,
            tags=[str(t) for t in (data.get("tags") or []) if t],
            visuals=[str(v) for v in (data.get("visuals") or []) if v],
        )


@dataclass
class TechnicalSpecifications:
    capabilities: list[str] = field(default_factory=list)
    compatible_platforms: list[str] = field(default_factory=list)
    compatible_products: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    source_license: str = ""

    def to_dict(self) -> dict:
        return {
            "capabilities": self.capabilities,
            "compatible_platforms": self.compatible_platforms,
            "compatible_products": self.compatible_products,
            "dependencies": self.dependencies,
            "protocols": self.protocols,
            "artifacts": self.artifacts,
            "source_license": self.source_license,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TechnicalSpecifications":
        return cls(
            capabilities=[str(c) for c in (data.get("capabilities") or []) if c],
            compatible_platforms=[str(p) for p in (data.get("compatible_platforms") or []) if p],
            compatible_products=[str(p) for p in (data.get("compatible_products") or []) if p],
            dependencies=[str(d) for d in (data.get("dependencies") or []) if d],
            protocols=[str(p) for p in (data.get("protocols") or []) if p],
            artifacts=[str(a) for a in (data.get("artifacts") or []) if a],
            source_license=str(data.get("source_license", "") or ""),
        )


@dataclass
class OrganizationalSpecifications:
    vendor_id: str = ""
    support_contact_id: str = ""
    support_status: str = ""

    def to_dict(self) -> dict:
        return {
            "vendor_id": self.vendor_id,
            "support_contact_id": self.support_contact_id,
            "support_status": self.support_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrganizationalSpecifications":
        return cls(
            vendor_id=str(data.get("vendor_id", "") or ""),
            support_contact_id=str(data.get("support_contact_id", "") or ""),
            support_status=str(data.get("support_status", "") or ""),
        )


@dataclass
class EntryMetadata:
    created_by: str = ""
    creation_date: str = ""
    last_update_date: str = field(default_factory=_today_str)

    def to_dict(self) -> dict:
        return {
            "created_by": self.created_by,
            "creation_date": self.creation_date,
            "last_update_date": self.last_update_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EntryMetadata":
        return cls(
            created_by=str(data.get("created_by", "") or ""),
            creation_date=str(data.get("creation_date", "") or ""),
            last_update_date=str(data.get("last_update_date", "") or ""),
        )


@dataclass
class Entry:
    """Represents a single integration entry YAML file."""
    id: str
    locales: dict[str, EntryLocale] = field(default_factory=lambda: {
        "en-US": EntryLocale(name="", short_description="", long_description=""),
        "de-DE": EntryLocale(name="", short_description="", long_description=""),
    })
    technical_specifications: TechnicalSpecifications = field(default_factory=TechnicalSpecifications)
    organizational_specifications: OrganizationalSpecifications = field(default_factory=OrganizationalSpecifications)
    metadata: EntryMetadata = field(default_factory=EntryMetadata)
    main_icon: str = ""
    version: str = ""
    # path set by loader; not serialised
    path: Optional[Path] = field(default=None, repr=False, compare=False)

    # Convenience properties for backward compatibility
    @property
    def en_US(self) -> EntryLocale:
        return self.locales.get("en-US", EntryLocale(name="", short_description="", long_description=""))

    @property
    def de_DE(self) -> EntryLocale:
        return self.locales.get("de-DE", EntryLocale(name="", short_description="", long_description=""))

    def locale(self, code: str) -> EntryLocale:
        """Return the locale for the given code, or a blank one."""
        return self.locales.get(code, EntryLocale(name="", short_description="", long_description=""))

    def locale_codes(self) -> list[str]:
        """Return sorted list of locale codes present on this entry."""
        return sorted(self.locales.keys())

    def validate(self) -> None:
        if not self.id.strip():
            raise ValidationError("Entry.id must not be empty.")
        for code in REQUIRED_LOCALES:
            if code not in self.locales:
                raise MissingLocaleError(
                    f"Entry '{self.id}' is missing required locale '{code}'."
                )
        for code, loc in self.locales.items():
            loc.validate()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": {
                code: loc.to_dict() for code, loc in self.locales.items()
            },
            "main_icon": self.main_icon,
            "version": self.version,
            "metadata": self.metadata.to_dict(),
            "organizational_specifications": self.organizational_specifications.to_dict(),
            "technical_specifications": self.technical_specifications.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, path: Optional[Path] = None) -> "Entry":
        desc = data.get("description") or {}
        locales = {
            code: EntryLocale.from_dict(locale_data)
            for code, locale_data in desc.items()
            if isinstance(locale_data, dict)
        }
        # Ensure required locales are present (with empty defaults)
        for code in REQUIRED_LOCALES:
            if code not in locales:
                locales[code] = EntryLocale.from_dict({})
        return cls(
            id=str(data.get("id", "") or ""),
            locales=locales,
            technical_specifications=TechnicalSpecifications.from_dict(
                data.get("technical_specifications") or {}
            ),
            organizational_specifications=OrganizationalSpecifications.from_dict(
                data.get("organizational_specifications") or {}
            ),
            metadata=EntryMetadata.from_dict(data.get("metadata") or {}),
            main_icon=str(data.get("main_icon", "") or ""),
            version=str(data.get("version", "") or ""),
            path=path,
        )
