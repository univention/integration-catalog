# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""Exceptions for the integration catalog library."""


class CatalogError(Exception):
    """Base exception for all catalog errors."""


class ValidationError(CatalogError):
    """Raised when a data model fails validation."""


class NotFoundError(CatalogError):
    """Raised when a requested element does not exist."""


class DuplicateIdError(CatalogError):
    """Raised when an element with the same ID already exists."""


class MissingLocaleError(ValidationError):
    """Raised when a required locale (de-DE or en-US) is missing."""


class InvalidReferenceError(ValidationError):
    """Raised when an entry references a definition or organization ID that does not exist."""
