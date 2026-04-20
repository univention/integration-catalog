# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""Integration Catalog library for managing Univention integration entries."""

from .catalog import Catalog
from .models import (
    validate_markdown,
    LocalizedText,
    OrganizationLocale,
    Organization,
    DefinitionItem,
    DefinitionFile,
    EntryLocale,
    TechnicalSpecifications,
    OrganizationalSpecifications,
    EntryMetadata,
    Entry,
)
from .exceptions import (
    CatalogError,
    ValidationError,
    NotFoundError,
    DuplicateIdError,
    MissingLocaleError,
    InvalidReferenceError,
)

__all__ = [
    "Catalog",
    "validate_markdown",
    "LocalizedText",
    "OrganizationLocale",
    "Organization",
    "DefinitionItem",
    "DefinitionFile",
    "EntryLocale",
    "TechnicalSpecifications",
    "OrganizationalSpecifications",
    "EntryMetadata",
    "Entry",
    "CatalogError",
    "ValidationError",
    "NotFoundError",
    "DuplicateIdError",
    "MissingLocaleError",
    "InvalidReferenceError",
]
