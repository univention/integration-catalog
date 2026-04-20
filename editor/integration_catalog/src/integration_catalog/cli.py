# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""
Command-line tool for CRUD operations on the Univention Integration Catalog.

Usage examples
--------------

  # Validate the entire catalog
  integration-catalog --root /path/to/catalog validate

  # List all definition types
  integration-catalog --root . definition list-types

  # List items of a definition type
  integration-catalog --root . definition list artifacts

  # Add a new artifact definition
  integration-catalog --root . definition add artifacts \\
      --id my_artifact \\
      --en-name "My Artifact" --en-description "Does something" \\
      --de-name "Mein Artefakt" --de-description "Macht etwas"

  # List all organizations
  integration-catalog --root . org list

  # Show one organization
  integration-catalog --root . org show univention

  # Add a new organization
  integration-catalog --root . org add \\
      --id example-corp \\
      --en-name "Example Corp" --en-short "Example Corp" \\
      --de-name "Example Corp" --de-short "Example Corp" \\
      --link https://example.com --contact info@example.com

  # Update an organization field
  integration-catalog --root . org update example-corp \\
      --en-name "Example Corporation"

  # Remove an organization
  integration-catalog --root . org remove example-corp

  # List all entries
  integration-catalog --root . entry list

  # Show one entry
  integration-catalog --root . entry show COMMUNITY-gitlab-ucs-ldap

  # Add a new entry
  integration-catalog --root . entry add \\
      --id COMMUNITY-my-app \\
      --en-name "My App" --en-short "My App integration" \\
      --en-long "Long description in English." \\
      --de-name "Meine App" --de-short "Meine App Integration" \\
      --de-long "Lange Beschreibung auf Deutsch."

  # Remove an entry
  integration-catalog --root . entry remove COMMUNITY-my-app
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box

from .catalog import Catalog
from .exceptions import CatalogError
from .models import (
    DefinitionItem,
    Entry,
    EntryLocale,
    EntryMetadata,
    LocalizedText,
    Organization,
    OrganizationLocale,
    OrgMetadata,
    OrganizationalSpecifications,
    TechnicalSpecifications,
    _today_str,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--root",
    default=".",
    show_default=True,
    help="Path to the root of the integration catalog repository.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.pass_context
def main(ctx: click.Context, root: Path) -> None:
    """Manage the Univention Integration Catalog."""
    ctx.ensure_object(dict)
    ctx.obj["root"] = root


def _load(ctx: click.Context) -> Catalog:
    try:
        return Catalog.load(ctx.obj["root"])
    except CatalogError as exc:
        err_console.print(f"[bold red]Error loading catalog:[/bold red] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate all definitions, organizations, and entries in the catalog."""
    catalog = _load(ctx)
    errors = catalog.validate()
    if not errors:
        console.print("[bold green]✓ Catalog is valid.[/bold green]")
    else:
        console.print(f"[bold red]✗ Found {len(errors)} validation error(s):[/bold red]")
        for err in errors:
            console.print(f"  • {err}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# definition group
# ---------------------------------------------------------------------------

@main.group("definition")
def definition_group() -> None:
    """CRUD operations for definition items (artifacts, capabilities, …)."""


@definition_group.command("list-types")
@click.pass_context
def definition_list_types(ctx: click.Context) -> None:
    """List all available definition types."""
    catalog = _load(ctx)
    types = catalog.definition_types()
    t = Table("Type", "Items", box=box.SIMPLE)
    for dt in types:
        df = catalog.definitions[dt]
        t.add_row(dt, str(len(df.items)))
    console.print(t)


@definition_group.command("list")
@click.argument("definition_type")
@click.pass_context
def definition_list(ctx: click.Context, definition_type: str) -> None:
    """List all items of DEFINITION_TYPE."""
    catalog = _load(ctx)
    try:
        items = catalog.list_definitions(definition_type)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    t = Table("ID", "en-US name", "de-DE name", box=box.SIMPLE)
    for item in items:
        t.add_row(item.id, item.en_US.name, item.de_DE.name)
    console.print(t)


@definition_group.command("show")
@click.argument("definition_type")
@click.argument("item_id")
@click.pass_context
def definition_show(ctx: click.Context, definition_type: str, item_id: str) -> None:
    """Show details of a single definition item."""
    catalog = _load(ctx)
    try:
        item = catalog.get_definition(definition_type, item_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[bold]ID:[/bold] {item.id}")
    console.print(f"[bold]en-US name:[/bold] {item.en_US.name}")
    console.print(f"[bold]en-US description:[/bold] {item.en_US.description}")
    console.print(f"[bold]de-DE name:[/bold] {item.de_DE.name}")
    console.print(f"[bold]de-DE description:[/bold] {item.de_DE.description}")


@definition_group.command("add")
@click.argument("definition_type")
@click.option("--id", "item_id", required=True, help="Unique identifier for the new item.")
@click.option("--en-name", required=True, help="English name.")
@click.option("--en-description", required=True, help="English description.")
@click.option("--de-name", required=True, help="German name.")
@click.option("--de-description", required=True, help="German description.")
@click.pass_context
def definition_add(
    ctx: click.Context,
    definition_type: str,
    item_id: str,
    en_name: str,
    en_description: str,
    de_name: str,
    de_description: str,
) -> None:
    """Add a new item to DEFINITION_TYPE."""
    catalog = _load(ctx)
    item = DefinitionItem(
        id=item_id,
        en_US=LocalizedText(name=en_name, description=en_description),
        de_DE=LocalizedText(name=de_name, description=de_description),
    )
    try:
        catalog.add_definition(definition_type, item)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Added definition '{item_id}' to '{definition_type}'.[/green]")


@definition_group.command("update")
@click.argument("definition_type")
@click.argument("item_id")
@click.option("--en-name", default=None, help="New English name.")
@click.option("--en-description", default=None, help="New English description.")
@click.option("--de-name", default=None, help="New German name.")
@click.option("--de-description", default=None, help="New German description.")
@click.pass_context
def definition_update(
    ctx: click.Context,
    definition_type: str,
    item_id: str,
    en_name: Optional[str],
    en_description: Optional[str],
    de_name: Optional[str],
    de_description: Optional[str],
) -> None:
    """Update an existing definition item (only supplied fields are changed)."""
    catalog = _load(ctx)
    try:
        existing = catalog.get_definition(definition_type, item_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    updated = DefinitionItem(
        id=item_id,
        en_US=LocalizedText(
            name=en_name if en_name is not None else existing.en_US.name,
            description=en_description if en_description is not None else existing.en_US.description,
        ),
        de_DE=LocalizedText(
            name=de_name if de_name is not None else existing.de_DE.name,
            description=de_description if de_description is not None else existing.de_DE.description,
        ),
    )
    try:
        catalog.update_definition(definition_type, updated)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Updated definition '{item_id}' in '{definition_type}'.[/green]")


@definition_group.command("remove")
@click.argument("definition_type")
@click.argument("item_id")
@click.confirmation_option(prompt="Are you sure you want to remove this definition?")
@click.pass_context
def definition_remove(ctx: click.Context, definition_type: str, item_id: str) -> None:
    """Remove a definition item (fails if any entry still references it)."""
    catalog = _load(ctx)
    try:
        catalog.remove_definition(definition_type, item_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Removed definition '{item_id}' from '{definition_type}'.[/green]")


# ---------------------------------------------------------------------------
# org group
# ---------------------------------------------------------------------------

@main.group("org")
def org_group() -> None:
    """CRUD operations for organizations."""


@org_group.command("list")
@click.pass_context
def org_list(ctx: click.Context) -> None:
    """List all organizations."""
    catalog = _load(ctx)
    orgs = catalog.list_organizations()
    t = Table("ID", "en-US name", "de-DE name", "Contact", box=box.SIMPLE)
    for org in sorted(orgs, key=lambda o: o.id):
        t.add_row(org.id, org.en_US.name, org.de_DE.name, org.en_US.contact or "—")
    console.print(t)


@org_group.command("show")
@click.argument("org_id")
@click.pass_context
def org_show(ctx: click.Context, org_id: str) -> None:
    """Show details of an organization."""
    catalog = _load(ctx)
    try:
        org = catalog.get_organization(org_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[bold]ID:[/bold]           {org.id}")
    console.print(f"[bold]Schema version:[/bold] {org.metadata.schema_version}")
    console.print(f"[bold]Last updated:[/bold]   {org.metadata.last_updated}")
    console.print()
    for locale, loc_obj in (("en-US", org.en_US), ("de-DE", org.de_DE)):
        console.print(f"[bold underline]{locale}[/bold underline]")
        console.print(f"  name:              {loc_obj.name}")
        console.print(f"  short_description: {loc_obj.short_description}")
        console.print(f"  link:              {loc_obj.link or '—'}")
        console.print(f"  contact:           {loc_obj.contact or '—'}")
        console.print(f"  logo:              {loc_obj.logo or '—'}")
        console.print()
    if org.path:
        console.print(f"[dim]File: {org.path}[/dim]")


@org_group.command("add")
@click.option("--id", "org_id", required=True, help="Unique organization ID (letters, digits, hyphens, underscores).")
@click.option("--en-name", required=True, help="English name.")
@click.option("--en-short", required=True, help="English short description.")
@click.option("--de-name", required=True, help="German name.")
@click.option("--de-short", required=True, help="German short description.")
@click.option("--link", default="", help="Website URL (used for both locales unless overridden).")
@click.option("--contact", default="", help="Contact email (used for both locales unless overridden).")
@click.option("--en-link", default=None, help="English-specific website URL.")
@click.option("--de-link", default=None, help="German-specific website URL.")
@click.option("--en-contact", default=None, help="English-specific contact email.")
@click.option("--de-contact", default=None, help="German-specific contact email.")
@click.option("--en-logo", default="", help="English logo filename.")
@click.option("--de-logo", default="", help="German logo filename.")
@click.pass_context
def org_add(
    ctx: click.Context,
    org_id: str,
    en_name: str,
    en_short: str,
    de_name: str,
    de_short: str,
    link: str,
    contact: str,
    en_link: Optional[str],
    de_link: Optional[str],
    en_contact: Optional[str],
    de_contact: Optional[str],
    en_logo: str,
    de_logo: str,
) -> None:
    """Add a new organization."""
    catalog = _load(ctx)
    org = Organization(
        id=org_id,
        en_US=OrganizationLocale(
            name=en_name,
            short_description=en_short,
            link=en_link if en_link is not None else link,
            contact=en_contact if en_contact is not None else contact,
            logo=en_logo,
        ),
        de_DE=OrganizationLocale(
            name=de_name,
            short_description=de_short,
            link=de_link if de_link is not None else link,
            contact=de_contact if de_contact is not None else contact,
            logo=de_logo,
        ),
        metadata=OrgMetadata(),
    )
    try:
        catalog.add_organization(org)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Added organization '{org_id}'.[/green]")
    if org.path:
        console.print(f"[dim]Written to: {org.path}[/dim]")


@org_group.command("update")
@click.argument("org_id")
@click.option("--en-name", default=None)
@click.option("--en-short", default=None)
@click.option("--en-link", default=None)
@click.option("--en-contact", default=None)
@click.option("--en-logo", default=None)
@click.option("--de-name", default=None)
@click.option("--de-short", default=None)
@click.option("--de-link", default=None)
@click.option("--de-contact", default=None)
@click.option("--de-logo", default=None)
@click.pass_context
def org_update(
    ctx: click.Context,
    org_id: str,
    en_name: Optional[str],
    en_short: Optional[str],
    en_link: Optional[str],
    en_contact: Optional[str],
    en_logo: Optional[str],
    de_name: Optional[str],
    de_short: Optional[str],
    de_link: Optional[str],
    de_contact: Optional[str],
    de_logo: Optional[str],
) -> None:
    """Update an existing organization (only supplied fields are changed)."""
    catalog = _load(ctx)
    try:
        existing = catalog.get_organization(org_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    updated = Organization(
        id=org_id,
        en_US=OrganizationLocale(
            name=en_name if en_name is not None else existing.en_US.name,
            short_description=en_short if en_short is not None else existing.en_US.short_description,
            link=en_link if en_link is not None else existing.en_US.link,
            contact=en_contact if en_contact is not None else existing.en_US.contact,
            logo=en_logo if en_logo is not None else existing.en_US.logo,
        ),
        de_DE=OrganizationLocale(
            name=de_name if de_name is not None else existing.de_DE.name,
            short_description=de_short if de_short is not None else existing.de_DE.short_description,
            link=de_link if de_link is not None else existing.de_DE.link,
            contact=de_contact if de_contact is not None else existing.de_DE.contact,
            logo=de_logo if de_logo is not None else existing.de_DE.logo,
        ),
        metadata=existing.metadata,
    )
    try:
        catalog.update_organization(updated)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Updated organization '{org_id}'.[/green]")


@org_group.command("remove")
@click.argument("org_id")
@click.confirmation_option(prompt="Are you sure you want to remove this organization?")
@click.pass_context
def org_remove(ctx: click.Context, org_id: str) -> None:
    """Remove an organization (fails if any entry still references it)."""
    catalog = _load(ctx)
    try:
        catalog.remove_organization(org_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Removed organization '{org_id}'.[/green]")


# ---------------------------------------------------------------------------
# entry group
# ---------------------------------------------------------------------------

@main.group("entry")
def entry_group() -> None:
    """CRUD operations for integration entries."""


@entry_group.command("list")
@click.pass_context
def entry_list(ctx: click.Context) -> None:
    """List all entries."""
    catalog = _load(ctx)
    entries = catalog.list_entries()
    t = Table("ID", "en-US name", "Vendor", "Products", "Platforms", "Artifacts", box=box.SIMPLE)
    for entry in sorted(entries, key=lambda e: e.id):
        ts = entry.technical_specifications
        os = entry.organizational_specifications
        t.add_row(
            entry.id,
            entry.en_US.name or "—",
            os.vendor_id or "—",
            ", ".join(ts.compatible_products) or "—",
            ", ".join(ts.compatible_platforms) or "—",
            ", ".join(ts.artifacts) or "—",
        )
    console.print(t)


@entry_group.command("show")
@click.argument("entry_id")
@click.pass_context
def entry_show(ctx: click.Context, entry_id: str) -> None:
    """Show details of an entry."""
    catalog = _load(ctx)
    try:
        entry = catalog.get_entry(entry_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)

    console.print(f"[bold]ID:[/bold]       {entry.id}")
    console.print(f"[bold]Version:[/bold]  {entry.version or '—'}")
    console.print(f"[bold]Main icon:[/bold] {entry.main_icon or '—'}")
    console.print()

    ts = entry.technical_specifications
    os_spec = entry.organizational_specifications
    console.print("[bold underline]Organizational Specifications[/bold underline]")
    console.print(f"  vendor_id:          {os_spec.vendor_id or '—'}")
    console.print(f"  support_contact_id: {os_spec.support_contact_id or '—'}")
    console.print(f"  support_status:     {os_spec.support_status or '—'}")
    console.print()
    console.print("[bold underline]Technical Specifications[/bold underline]")
    console.print(f"  capabilities:        {', '.join(ts.capabilities) or '—'}")
    console.print(f"  artifacts:           {', '.join(ts.artifacts) or '—'}")
    console.print(f"  protocols:           {', '.join(ts.protocols) or '—'}")
    console.print(f"  compatible_products: {', '.join(ts.compatible_products) or '—'}")
    console.print(f"  compatible_platforms:{', '.join(ts.compatible_platforms) or '—'}")
    console.print()

    for locale, loc_obj in (("en-US", entry.en_US), ("de-DE", entry.de_DE)):
        console.print(f"[bold underline]{locale}[/bold underline]")
        console.print(f"  name:              {loc_obj.name}")
        console.print(f"  short_description: {loc_obj.short_description}")
        console.print(f"  keywords:          {', '.join(loc_obj.keywords) or '—'}")
        console.print(f"  long_description:")
        for line in loc_obj.long_description.splitlines():
            console.print(f"    {line}")
        console.print()

    if entry.path:
        console.print(f"[dim]File: {entry.path}[/dim]")


@entry_group.command("add")
@click.option("--id", "entry_id", required=True, help="Unique entry ID.")
@click.option("--en-name", required=True, help="English name.")
@click.option("--en-short", required=True, help="English short description.")
@click.option("--en-long", required=True, help="English long description.")
@click.option("--de-name", required=True, help="German name.")
@click.option("--de-short", required=True, help="German short description.")
@click.option("--de-long", required=True, help="German long description.")
@click.option("--vendor-id", default="", help="Organization ID of the vendor.")
@click.option("--support-contact-id", default="", help="Organization ID of the support contact.")
@click.option("--support-status", default="", help="Support status (e.g. 'Enterprise').")
@click.option("--products", default="", help="Comma-separated list of compatible_products.")
@click.option("--platforms", default="", help="Comma-separated list of compatible_platforms.")
@click.option("--capabilities", default="", help="Comma-separated list of capabilities.")
@click.option("--artifacts", default="", help="Comma-separated list of artifacts.")
@click.option("--protocols", default="", help="Comma-separated list of protocols.")
@click.option("--version", default="", help="Version string.")
@click.option("--created-by", default="", help="Creator name.")
@click.pass_context
def entry_add(
    ctx: click.Context,
    entry_id: str,
    en_name: str,
    en_short: str,
    en_long: str,
    de_name: str,
    de_short: str,
    de_long: str,
    vendor_id: str,
    support_contact_id: str,
    support_status: str,
    products: str,
    platforms: str,
    capabilities: str,
    artifacts: str,
    protocols: str,
    version: str,
    created_by: str,
) -> None:
    """Add a new integration entry."""
    catalog = _load(ctx)

    def _split(val: str) -> list[str]:
        return [v.strip() for v in val.split(",") if v.strip()] if val else []

    today = _today_str()
    entry = Entry(
        id=entry_id,
        en_US=EntryLocale(
            name=en_name,
            short_description=en_short,
            long_description=en_long,
        ),
        de_DE=EntryLocale(
            name=de_name,
            short_description=de_short,
            long_description=de_long,
        ),
        organizational_specifications=OrganizationalSpecifications(
            vendor_id=vendor_id,
            support_contact_id=support_contact_id,
            support_status=support_status,
        ),
        technical_specifications=TechnicalSpecifications(
            compatible_products=_split(products),
            compatible_platforms=_split(platforms),
            capabilities=_split(capabilities),
            artifacts=_split(artifacts),
            protocols=_split(protocols),
        ),
        metadata=EntryMetadata(
            created_by=created_by,
            creation_date=today,
            last_update_date=today,
        ),
        version=version,
    )

    try:
        catalog.add_entry(entry)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)

    console.print(f"[green]Added entry '{entry_id}'.[/green]")
    if entry.path:
        console.print(f"[dim]Written to: {entry.path}[/dim]")


@entry_group.command("update")
@click.argument("entry_id")
@click.option("--en-name", default=None)
@click.option("--en-short", default=None)
@click.option("--en-long", default=None)
@click.option("--de-name", default=None)
@click.option("--de-short", default=None)
@click.option("--de-long", default=None)
@click.option("--vendor-id", default=None)
@click.option("--support-contact-id", default=None)
@click.option("--support-status", default=None)
@click.option("--products", default=None, help="Comma-separated list; replaces existing.")
@click.option("--platforms", default=None, help="Comma-separated list; replaces existing.")
@click.option("--capabilities", default=None, help="Comma-separated list; replaces existing.")
@click.option("--artifacts", default=None, help="Comma-separated list; replaces existing.")
@click.option("--protocols", default=None, help="Comma-separated list; replaces existing.")
@click.option("--version", default=None)
@click.pass_context
def entry_update(
    ctx: click.Context,
    entry_id: str,
    en_name: Optional[str],
    en_short: Optional[str],
    en_long: Optional[str],
    de_name: Optional[str],
    de_short: Optional[str],
    de_long: Optional[str],
    vendor_id: Optional[str],
    support_contact_id: Optional[str],
    support_status: Optional[str],
    products: Optional[str],
    platforms: Optional[str],
    capabilities: Optional[str],
    artifacts: Optional[str],
    protocols: Optional[str],
    version: Optional[str],
) -> None:
    """Update an existing entry (only supplied options are changed)."""
    catalog = _load(ctx)
    try:
        existing = catalog.get_entry(entry_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)

    def _split(val: str) -> list[str]:
        return [v.strip() for v in val.split(",") if v.strip()]

    ts = existing.technical_specifications
    os_spec = existing.organizational_specifications

    updated = Entry(
        id=entry_id,
        en_US=EntryLocale(
            name=en_name if en_name is not None else existing.en_US.name,
            short_description=en_short if en_short is not None else existing.en_US.short_description,
            long_description=en_long if en_long is not None else existing.en_US.long_description,
            icon=existing.en_US.icon,
            keywords=existing.en_US.keywords,
            links=existing.en_US.links,
            tags=existing.en_US.tags,
            visuals=existing.en_US.visuals,
        ),
        de_DE=EntryLocale(
            name=de_name if de_name is not None else existing.de_DE.name,
            short_description=de_short if de_short is not None else existing.de_DE.short_description,
            long_description=de_long if de_long is not None else existing.de_DE.long_description,
            icon=existing.de_DE.icon,
            keywords=existing.de_DE.keywords,
            links=existing.de_DE.links,
            tags=existing.de_DE.tags,
            visuals=existing.de_DE.visuals,
        ),
        organizational_specifications=OrganizationalSpecifications(
            vendor_id=vendor_id if vendor_id is not None else os_spec.vendor_id,
            support_contact_id=support_contact_id if support_contact_id is not None else os_spec.support_contact_id,
            support_status=support_status if support_status is not None else os_spec.support_status,
        ),
        technical_specifications=TechnicalSpecifications(
            compatible_products=_split(products) if products is not None else ts.compatible_products,
            compatible_platforms=_split(platforms) if platforms is not None else ts.compatible_platforms,
            capabilities=_split(capabilities) if capabilities is not None else ts.capabilities,
            artifacts=_split(artifacts) if artifacts is not None else ts.artifacts,
            protocols=_split(protocols) if protocols is not None else ts.protocols,
            source_license=ts.source_license,
        ),
        metadata=existing.metadata,
        main_icon=existing.main_icon,
        version=version if version is not None else existing.version,
    )

    try:
        catalog.update_entry(updated)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Updated entry '{entry_id}'.[/green]")


@entry_group.command("remove")
@click.argument("entry_id")
@click.confirmation_option(prompt="Are you sure you want to remove this entry?")
@click.pass_context
def entry_remove(ctx: click.Context, entry_id: str) -> None:
    """Remove an entry YAML file."""
    catalog = _load(ctx)
    try:
        catalog.remove_entry(entry_id)
    except CatalogError as exc:
        err_console.print(str(exc))
        sys.exit(1)
    console.print(f"[green]Removed entry '{entry_id}'.[/green]")
