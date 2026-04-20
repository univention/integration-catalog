# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""
Streamlit web UI for the Univention Integration Catalog editor.

Launch with:
    streamlit run /path/to/ui.py -- --root /path/to/catalog
or via the installed entry point:
    integration-catalog-ui --root /path/to/catalog
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Integration Catalog Editor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

from .catalog import Catalog
from .exceptions import CatalogError
from .models import (
    DefinitionFile,
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

# ---------------------------------------------------------------------------
# Catalog root resolution
# ---------------------------------------------------------------------------

def _resolve_root() -> Path:
    """Return the catalog root from CLI args (``-- --root PATH``) or cwd."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--root", "-r") and i + 1 < len(args):
            return Path(args[i + 1]).resolve()
    return Path(".").resolve()


CATALOG_ROOT = _resolve_root()

# ---------------------------------------------------------------------------
# Cached catalog loader — reload on demand via session state flag
# ---------------------------------------------------------------------------

def _load_catalog() -> Catalog:
    try:
        return Catalog.load(CATALOG_ROOT)
    except CatalogError as exc:
        st.error(f"❌ Failed to load catalog from `{CATALOG_ROOT}`:\n\n{exc}")
        st.stop()


def get_catalog() -> Catalog:
    """Return a cached Catalog, reloading if the reload flag is set."""
    if st.session_state.get("_reload", True):
        st.session_state["catalog"] = _load_catalog()
        st.session_state["_reload"] = False
    return st.session_state["catalog"]


def reload_catalog() -> None:
    """Signal that the catalog should be reloaded on the next access."""
    st.session_state["_reload"] = True


# ---------------------------------------------------------------------------
# Helper: build option lists for reference selectors
# ---------------------------------------------------------------------------

def _org_options(catalog: Catalog, include_empty: bool = True) -> list[str]:
    orgs = sorted(catalog.organizations.keys())
    return ([""] if include_empty else []) + orgs


def _org_label(catalog: Catalog, org_id: str) -> str:
    if not org_id:
        return "— (none)"
    org = catalog.organizations.get(org_id)
    if org:
        return f"{org_id}  —  {org.en_US.name}"
    return org_id


def _def_options(catalog: Catalog, def_type: str) -> list[str]:
    df = catalog.definitions.get(def_type)
    if df is None:
        return []
    return [item.id for item in df.items]


def _def_label(catalog: Catalog, def_type: str, item_id: str) -> str:
    df = catalog.definitions.get(def_type)
    if df is None:
        return item_id
    item = df.get(item_id)
    if item:
        return f"{item_id}  —  {item.en_US.name}"
    return item_id


# ---------------------------------------------------------------------------
# Reusable UI components
# ---------------------------------------------------------------------------

def _success(msg: str) -> None:
    st.success(f"✅ {msg}")
    reload_catalog()


def _error(msg: str) -> None:
    st.error(f"❌ {msg}")


def _confirm_delete(key: str, label: str) -> bool:
    """Show a confirmation checkbox before allowing deletion."""
    return st.checkbox(f"Confirm deletion of **{label}**", key=key)


def _locale_fields(
    prefix: str,
    locale_label: str,
    defaults: Optional[dict] = None,
) -> dict:
    """Render text inputs for one locale block and return a dict of values."""
    d = defaults or {}
    st.markdown(f"**{locale_label}**")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name *", value=d.get("name", ""), key=f"{prefix}_name")
        short = st.text_input("Short description *", value=d.get("short_description", ""), key=f"{prefix}_short")
        link = st.text_input("Website link", value=d.get("link", ""), key=f"{prefix}_link")
    with col2:
        contact = st.text_input("Contact email", value=d.get("contact", ""), key=f"{prefix}_contact")
        logo = st.text_input("Logo filename", value=d.get("logo", ""), key=f"{prefix}_logo")
    return {"name": name, "short_description": short, "link": link, "contact": contact, "logo": logo}


def _entry_locale_fields(prefix: str, locale_label: str, defaults: Optional[EntryLocale] = None) -> dict:
    """Render the full entry locale block."""
    d = defaults
    st.markdown(f"**{locale_label}**")
    name = st.text_input("Name *", value=d.name if d else "", key=f"{prefix}_name")
    short = st.text_input(
        "Short description *",
        value=d.short_description if d else "",
        key=f"{prefix}_short",
        help="Plain text or markdown. Must not contain unclosed HTML tags.",
    )
    long_desc = st.text_area(
        "Long description * (Markdown)",
        value=d.long_description if d else "",
        height=200,
        key=f"{prefix}_long",
        help="Supports full Markdown: headings (#), lists (- or *), bold (**), links, code blocks.",
    )
    keywords_raw = st.text_input(
        "Keywords (comma-separated)",
        value=", ".join(d.keywords) if d else "",
        key=f"{prefix}_keywords",
    )
    return {
        "name": name,
        "short_description": short,
        "long_description": long_desc,
        "keywords": [k.strip() for k in keywords_raw.split(",") if k.strip()],
    }


# ---------------------------------------------------------------------------
# Page: Definitions
# ---------------------------------------------------------------------------

_DEF_TYPE_LABELS = {
    "artifacts": "Artifacts",
    "capabilities": "Capabilities",
    "platforms": "Platforms",
    "univention_products": "Univention Products",
}

_EDITABLE_DEF_TYPES = list(_DEF_TYPE_LABELS.keys())


def page_definitions(catalog: Catalog) -> None:
    st.header("📐 Definitions")
    st.caption(
        "Definitions are the controlled vocabulary used in integration entries: "
        "artifact types, capabilities, deployment platforms and Univention products."
    )

    def_type = st.selectbox(
        "Definition type",
        _EDITABLE_DEF_TYPES,
        format_func=lambda t: _DEF_TYPE_LABELS.get(t, t),
        key="def_type_select",
    )

    tab_list, tab_add = st.tabs(["📋 List & Edit", "➕ Add new"])

    with tab_list:
        _definitions_list(catalog, def_type)

    with tab_add:
        _definitions_add(catalog, def_type)


def _definitions_list(catalog: Catalog, def_type: str) -> None:
    items = catalog.list_definitions(def_type)
    if not items:
        st.info("No items defined yet.")
        return

    for item in items:
        with st.expander(f"**{item.id}** — {item.en_US.name}", expanded=False):
            col_form, col_del = st.columns([5, 1])
            with col_form:
                with st.form(key=f"def_edit_{def_type}_{item.id}"):
                    st.markdown("**en-US**")
                    en_name = st.text_input("Name *", value=item.en_US.name, key=f"en_name_{item.id}")
                    en_desc = st.text_input("Description *", value=item.en_US.description, key=f"en_desc_{item.id}")
                    st.markdown("**de-DE**")
                    de_name = st.text_input("Name *", value=item.de_DE.name, key=f"de_name_{item.id}")
                    de_desc = st.text_input("Description *", value=item.de_DE.description, key=f"de_desc_{item.id}")
                    if st.form_submit_button("💾 Save changes"):
                        updated = DefinitionItem(
                            id=item.id,
                            en_US=LocalizedText(name=en_name, description=en_desc),
                            de_DE=LocalizedText(name=de_name, description=de_desc),
                        )
                        try:
                            catalog.update_definition(def_type, updated)
                            _success(f"Updated '{item.id}'.")
                        except CatalogError as exc:
                            _error(str(exc))

            with col_del:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if _confirm_delete(f"del_def_{def_type}_{item.id}", item.id):
                    if st.button("🗑️ Delete", key=f"del_btn_{def_type}_{item.id}"):
                        try:
                            catalog.remove_definition(def_type, item.id)
                            _success(f"Deleted '{item.id}'.")
                        except CatalogError as exc:
                            _error(str(exc))


def _definitions_add(catalog: Catalog, def_type: str) -> None:
    with st.form(key=f"def_add_{def_type}"):
        item_id = st.text_input("ID *", help="Unique identifier, e.g. `my_artifact`")
        st.markdown("**en-US**")
        en_name = st.text_input("Name *", key="add_en_name")
        en_desc = st.text_input("Description *", key="add_en_desc")
        st.markdown("**de-DE**")
        de_name = st.text_input("Name *", key="add_de_name")
        de_desc = st.text_input("Description *", key="add_de_desc")
        if st.form_submit_button("➕ Add"):
            if not item_id.strip():
                _error("ID is required.")
            else:
                new_item = DefinitionItem(
                    id=item_id.strip(),
                    en_US=LocalizedText(name=en_name, description=en_desc),
                    de_DE=LocalizedText(name=de_name, description=de_desc),
                )
                try:
                    catalog.add_definition(def_type, new_item)
                    _success(f"Added '{item_id}'.")
                except CatalogError as exc:
                    _error(str(exc))


# ---------------------------------------------------------------------------
# Page: Organizations
# ---------------------------------------------------------------------------

def page_organizations(catalog: Catalog) -> None:
    st.header("🏢 Organizations")
    st.caption(
        "Organizations are vendors and support contacts that can be referenced "
        "from integration entries."
    )

    tab_list, tab_add = st.tabs(["📋 List & Edit", "➕ Add new"])

    with tab_list:
        _orgs_list(catalog)

    with tab_add:
        _orgs_add(catalog)


def _orgs_list(catalog: Catalog) -> None:
    orgs = sorted(catalog.list_organizations(), key=lambda o: o.id)
    if not orgs:
        st.info("No organizations defined yet.")
        return

    search = st.text_input("🔍 Filter by ID or name", key="org_search")
    if search:
        s = search.lower()
        orgs = [o for o in orgs if s in o.id.lower() or s in o.en_US.name.lower()]

    for org in orgs:
        with st.expander(f"**{org.id}** — {org.en_US.name}", expanded=False):
            col_form, col_del = st.columns([5, 1])
            with col_form:
                with st.form(key=f"org_edit_{org.id}"):
                    col_en, col_de = st.columns(2)
                    with col_en:
                        st.markdown("**en-US**")
                        en_name = st.text_input("Name *", value=org.en_US.name, key=f"org_en_name_{org.id}")
                        en_short = st.text_input("Short description *", value=org.en_US.short_description, key=f"org_en_short_{org.id}")
                        en_link = st.text_input("Website", value=org.en_US.link, key=f"org_en_link_{org.id}")
                        en_contact = st.text_input("Contact", value=org.en_US.contact, key=f"org_en_contact_{org.id}")
                        en_logo = st.text_input("Logo file", value=org.en_US.logo, key=f"org_en_logo_{org.id}")
                    with col_de:
                        st.markdown("**de-DE**")
                        de_name = st.text_input("Name *", value=org.de_DE.name, key=f"org_de_name_{org.id}")
                        de_short = st.text_input("Short description *", value=org.de_DE.short_description, key=f"org_de_short_{org.id}")
                        de_link = st.text_input("Website", value=org.de_DE.link, key=f"org_de_link_{org.id}")
                        de_contact = st.text_input("Contact", value=org.de_DE.contact, key=f"org_de_contact_{org.id}")
                        de_logo = st.text_input("Logo file", value=org.de_DE.logo, key=f"org_de_logo_{org.id}")
                    if st.form_submit_button("💾 Save changes"):
                        updated = Organization(
                            id=org.id,
                            en_US=OrganizationLocale(en_name, en_short, en_link, en_contact, en_logo),
                            de_DE=OrganizationLocale(de_name, de_short, de_link, de_contact, de_logo),
                            metadata=org.metadata,
                        )
                        try:
                            catalog.update_organization(updated)
                            _success(f"Updated '{org.id}'.")
                        except CatalogError as exc:
                            _error(str(exc))

            with col_del:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if _confirm_delete(f"del_org_{org.id}", org.id):
                    if st.button("🗑️ Delete", key=f"del_org_btn_{org.id}"):
                        try:
                            catalog.remove_organization(org.id)
                            _success(f"Deleted '{org.id}'.")
                        except CatalogError as exc:
                            _error(str(exc))


def _orgs_add(catalog: Catalog) -> None:
    with st.form(key="org_add"):
        org_id = st.text_input("ID *", help="Unique identifier using letters, digits, hyphens, underscores.")
        col_en, col_de = st.columns(2)
        with col_en:
            st.markdown("**en-US**")
            en_name = st.text_input("Name *", key="new_org_en_name")
            en_short = st.text_input("Short description *", key="new_org_en_short")
            en_link = st.text_input("Website", key="new_org_en_link")
            en_contact = st.text_input("Contact email", key="new_org_en_contact")
            en_logo = st.text_input("Logo filename", key="new_org_en_logo")
        with col_de:
            st.markdown("**de-DE**")
            de_name = st.text_input("Name *", key="new_org_de_name")
            de_short = st.text_input("Short description *", key="new_org_de_short")
            de_link = st.text_input("Website", key="new_org_de_link")
            de_contact = st.text_input("Contact email", key="new_org_de_contact")
            de_logo = st.text_input("Logo filename", key="new_org_de_logo")
        if st.form_submit_button("➕ Add organization"):
            if not org_id.strip():
                _error("ID is required.")
            else:
                new_org = Organization(
                    id=org_id.strip(),
                    en_US=OrganizationLocale(en_name, en_short, en_link, en_contact, en_logo),
                    de_DE=OrganizationLocale(de_name, de_short, de_link, de_contact, de_logo),
                    metadata=OrgMetadata(),
                )
                try:
                    catalog.add_organization(new_org)
                    _success(f"Added organization '{org_id}'.")
                except CatalogError as exc:
                    _error(str(exc))


# ---------------------------------------------------------------------------
# Page: Entries
# ---------------------------------------------------------------------------

def page_entries(catalog: Catalog) -> None:
    st.header("📦 Integration Entries")
    st.caption("Integration entries describe how an application integrates with Univention Nubus or UCS@school.")

    tab_list, tab_add = st.tabs(["📋 List & Edit", "➕ Add new"])

    with tab_list:
        _entries_list(catalog)

    with tab_add:
        _entries_add(catalog)


def _entries_list(catalog: Catalog) -> None:
    entries = sorted(catalog.list_entries(), key=lambda e: e.id)
    if not entries:
        st.info("No entries found.")
        return

    search = st.text_input("🔍 Filter by ID or name", key="entry_search")
    if search:
        s = search.lower()
        entries = [e for e in entries if s in e.id.lower() or s in e.en_US.name.lower()]

    for entry in entries:
        label = f"**{entry.id}** — {entry.en_US.name or '(no name)'}"
        with st.expander(label, expanded=False):
            _entry_edit_form(catalog, entry)


def _entry_edit_form(catalog: Catalog, entry: Entry) -> None:
    col_form, col_del = st.columns([5, 1])

    with col_form:
        with st.form(key=f"entry_edit_{entry.id}"):
            st.markdown("### English (en-US)")
            en = _entry_locale_fields(f"edit_{entry.id}_en", "en-US", entry.en_US)

            st.markdown("### German (de-DE)")
            de = _entry_locale_fields(f"edit_{entry.id}_de", "de-DE", entry.de_DE)

            st.markdown("### Organizational specifications")
            org_options = _org_options(catalog, include_empty=True)
            org_labels = {o: _org_label(catalog, o) for o in org_options}

            col1, col2, col3 = st.columns(3)
            with col1:
                vendor_idx = org_options.index(entry.organizational_specifications.vendor_id) \
                    if entry.organizational_specifications.vendor_id in org_options else 0
                vendor_id = st.selectbox(
                    "Vendor",
                    org_options,
                    index=vendor_idx,
                    format_func=lambda o: org_labels[o],
                    key=f"edit_{entry.id}_vendor",
                )
            with col2:
                support_idx = org_options.index(entry.organizational_specifications.support_contact_id) \
                    if entry.organizational_specifications.support_contact_id in org_options else 0
                support_id = st.selectbox(
                    "Support contact",
                    org_options,
                    index=support_idx,
                    format_func=lambda o: org_labels[o],
                    key=f"edit_{entry.id}_support",
                )
            with col3:
                support_status = st.text_input(
                    "Support status",
                    value=entry.organizational_specifications.support_status,
                    key=f"edit_{entry.id}_status",
                )

            st.markdown("### Technical specifications")
            col_a, col_b = st.columns(2)

            cap_options = _def_options(catalog, "capabilities")
            art_options = _def_options(catalog, "artifacts")
            plat_options = _def_options(catalog, "platforms")
            prod_options = _def_options(catalog, "univention_products")

            with col_a:
                caps = st.multiselect(
                    "Capabilities",
                    cap_options,
                    default=[c for c in entry.technical_specifications.capabilities if c in cap_options],
                    format_func=lambda x: _def_label(catalog, "capabilities", x),
                    key=f"edit_{entry.id}_caps",
                )
                artifacts = st.multiselect(
                    "Artifacts",
                    art_options,
                    default=[a for a in entry.technical_specifications.artifacts if a in art_options],
                    format_func=lambda x: _def_label(catalog, "artifacts", x),
                    key=f"edit_{entry.id}_arts",
                )
                protocols = st.text_input(
                    "Protocols (comma-separated)",
                    value=", ".join(entry.technical_specifications.protocols),
                    key=f"edit_{entry.id}_protocols",
                )

            with col_b:
                products = st.multiselect(
                    "Compatible products",
                    prod_options,
                    default=[p for p in entry.technical_specifications.compatible_products if p in prod_options],
                    format_func=lambda x: _def_label(catalog, "univention_products", x),
                    key=f"edit_{entry.id}_prods",
                )
                platforms = st.multiselect(
                    "Compatible platforms",
                    plat_options,
                    default=[p for p in entry.technical_specifications.compatible_platforms if p in plat_options],
                    format_func=lambda x: _def_label(catalog, "platforms", x),
                    key=f"edit_{entry.id}_plats",
                )
                version = st.text_input(
                    "Version",
                    value=entry.version,
                    key=f"edit_{entry.id}_version",
                )

            if st.form_submit_button("💾 Save changes"):
                updated = Entry(
                    id=entry.id,
                    en_US=EntryLocale(
                        name=en["name"],
                        short_description=en["short_description"],
                        long_description=en["long_description"],
                        keywords=en["keywords"],
                        icon=entry.en_US.icon,
                        links=entry.en_US.links,
                        tags=entry.en_US.tags,
                        visuals=entry.en_US.visuals,
                    ),
                    de_DE=EntryLocale(
                        name=de["name"],
                        short_description=de["short_description"],
                        long_description=de["long_description"],
                        keywords=de["keywords"],
                        icon=entry.de_DE.icon,
                        links=entry.de_DE.links,
                        tags=entry.de_DE.tags,
                        visuals=entry.de_DE.visuals,
                    ),
                    organizational_specifications=OrganizationalSpecifications(
                        vendor_id=vendor_id,
                        support_contact_id=support_id,
                        support_status=support_status,
                    ),
                    technical_specifications=TechnicalSpecifications(
                        capabilities=caps,
                        artifacts=artifacts,
                        protocols=[p.strip() for p in protocols.split(",") if p.strip()],
                        compatible_products=products,
                        compatible_platforms=platforms,
                        source_license=entry.technical_specifications.source_license,
                    ),
                    metadata=entry.metadata,
                    main_icon=entry.main_icon,
                    version=version,
                )
                try:
                    catalog.update_entry(updated)
                    _success(f"Updated '{entry.id}'.")
                except CatalogError as exc:
                    _error(str(exc))

    with col_del:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if _confirm_delete(f"del_entry_{entry.id}", entry.id):
            if st.button("🗑️ Delete", key=f"del_entry_btn_{entry.id}"):
                try:
                    catalog.remove_entry(entry.id)
                    _success(f"Deleted '{entry.id}'.")
                except CatalogError as exc:
                    _error(str(exc))


def _entries_add(catalog: Catalog) -> None:
    org_options = _org_options(catalog, include_empty=True)
    org_labels = {o: _org_label(catalog, o) for o in org_options}
    cap_options = _def_options(catalog, "capabilities")
    art_options = _def_options(catalog, "artifacts")
    plat_options = _def_options(catalog, "platforms")
    prod_options = _def_options(catalog, "univention_products")

    with st.form(key="entry_add"):
        entry_id = st.text_input("Entry ID *", help="e.g. `COMMUNITY-my-app` or `UCSAPP-my-app`")
        version = st.text_input("Version", value="")

        st.markdown("### English (en-US)")
        en = _entry_locale_fields("new_entry_en", "en-US")

        st.markdown("### German (de-DE)")
        de = _entry_locale_fields("new_entry_de", "de-DE")

        st.markdown("### Organizational specifications")
        col1, col2, col3 = st.columns(3)
        with col1:
            vendor_id = st.selectbox(
                "Vendor",
                org_options,
                format_func=lambda o: org_labels[o],
                key="new_entry_vendor",
            )
        with col2:
            support_id = st.selectbox(
                "Support contact",
                org_options,
                format_func=lambda o: org_labels[o],
                key="new_entry_support",
            )
        with col3:
            support_status = st.text_input("Support status", key="new_entry_status")

        st.markdown("### Technical specifications")
        col_a, col_b = st.columns(2)
        with col_a:
            caps = st.multiselect(
                "Capabilities",
                cap_options,
                format_func=lambda x: _def_label(catalog, "capabilities", x),
                key="new_entry_caps",
            )
            artifacts = st.multiselect(
                "Artifacts",
                art_options,
                format_func=lambda x: _def_label(catalog, "artifacts", x),
                key="new_entry_arts",
            )
            protocols = st.text_input("Protocols (comma-separated)", key="new_entry_protocols")
        with col_b:
            products = st.multiselect(
                "Compatible products",
                prod_options,
                format_func=lambda x: _def_label(catalog, "univention_products", x),
                key="new_entry_prods",
            )
            platforms = st.multiselect(
                "Compatible platforms",
                plat_options,
                format_func=lambda x: _def_label(catalog, "platforms", x),
                key="new_entry_plats",
            )

        if st.form_submit_button("➕ Add entry"):
            if not entry_id.strip():
                _error("Entry ID is required.")
            else:
                today = _today_str()
                new_entry = Entry(
                    id=entry_id.strip(),
                    en_US=EntryLocale(
                        name=en["name"],
                        short_description=en["short_description"],
                        long_description=en["long_description"],
                        keywords=en["keywords"],
                    ),
                    de_DE=EntryLocale(
                        name=de["name"],
                        short_description=de["short_description"],
                        long_description=de["long_description"],
                        keywords=de["keywords"],
                    ),
                    organizational_specifications=OrganizationalSpecifications(
                        vendor_id=vendor_id,
                        support_contact_id=support_id,
                        support_status=support_status,
                    ),
                    technical_specifications=TechnicalSpecifications(
                        capabilities=caps,
                        artifacts=artifacts,
                        protocols=[p.strip() for p in protocols.split(",") if p.strip()],
                        compatible_products=products,
                        compatible_platforms=platforms,
                    ),
                    metadata=EntryMetadata(creation_date=today, last_update_date=today),
                    version=version,
                )
                try:
                    catalog.add_entry(new_entry)
                    _success(f"Added entry '{entry_id}'.")
                except CatalogError as exc:
                    _error(str(exc))


# ---------------------------------------------------------------------------
# Page: Validate
# ---------------------------------------------------------------------------

def page_validate(catalog: Catalog) -> None:
    st.header("✅ Validate Catalog")
    st.caption("Checks all definitions, organizations and entries for consistency and completeness.")

    if st.button("▶ Run validation"):
        errors = catalog.validate()
        if not errors:
            st.success("✅ The catalog is valid — no errors found.")
        else:
            st.error(f"❌ Found **{len(errors)}** validation error(s):")
            for err in errors:
                st.markdown(f"- {err}")


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

_PAGES = {
    "📐 Definitions": page_definitions,
    "🏢 Organizations": page_organizations,
    "📦 Entries": page_entries,
    "✅ Validate": page_validate,
}


def _sidebar(catalog: Catalog) -> None:
    with st.sidebar:
        st.image(
            "https://www.univention.com/wp-content/uploads/2024/01/univention-logo.svg",
            width=200,
        )
        st.markdown("## Integration Catalog Editor")
        st.caption(f"Catalog root:\n`{CATALOG_ROOT}`")
        st.divider()

        st.markdown(
            f"**{len(catalog.definitions)}** definition types &nbsp;·&nbsp; "
            f"**{len(catalog.organizations)}** organizations &nbsp;·&nbsp; "
            f"**{len(catalog.entries)}** entries"
        )
        st.divider()

        if st.button("🔄 Reload catalog from disk"):
            reload_catalog()
            st.rerun()

        st.divider()
        st.caption("Select a section:")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _run_ui() -> None:
    catalog = get_catalog()
    _sidebar(catalog)

    page_name = st.sidebar.radio(
        "Navigation",
        list(_PAGES.keys()),
        label_visibility="collapsed",
    )

    _PAGES[page_name](catalog)  # type: ignore[operator]


def main() -> None:
    """Entry point when launched via ``integration-catalog-ui``."""
    # Streamlit re-runs this module on every interaction; _run_ui() does the work.
    _run_ui()


# Run when invoked directly by Streamlit
_run_ui()
