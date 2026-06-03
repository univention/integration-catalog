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

import subprocess
import sys
from pathlib import Path
from typing import Optional

# When Streamlit runs ui.py directly it is not part of a package, so relative
# imports fail. Ensure the src/ directory is on sys.path so absolute imports work.
_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

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

from integration_catalog.catalog import Catalog
from integration_catalog.exceptions import CatalogError
from integration_catalog.models import (
    REQUIRED_LOCALES,
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
        return f"{org.en_US.name} ({org_id})"
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


def _delete_with_confirmation(key: str, label: str, on_confirm: callable) -> None:
    """Two-step delete: show a delete button, then a confirmation checkbox + confirm button.

    *on_confirm* is called (with no arguments) when the user confirms deletion.
    """
    state_key = f"_del_pending_{key}"

    if st.button("🗑️ Delete", key=f"{key}_btn"):
        st.session_state[state_key] = True

    if st.session_state.get(state_key, False):
        confirmed = st.checkbox(f"Confirm deletion of **{label}**", key=f"{key}_confirm")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Confirm", key=f"{key}_yes", disabled=not confirmed):
                on_confirm()
                st.session_state.pop(state_key, None)
                st.rerun()
        with col_no:
            if st.button("Cancel", key=f"{key}_no"):
                st.session_state.pop(state_key, None)
                st.rerun()


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

            def _make_del_def(dt=def_type, iid=item.id):
                def _do():
                    try:
                        catalog.remove_definition(dt, iid)
                        _success(f"Deleted '{iid}'.")
                    except CatalogError as exc:
                        _error(str(exc))
                return _do

            _delete_with_confirmation(f"del_def_{def_type}_{item.id}", item.id, _make_del_def())


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

            def _make_del_org(oid=org.id):
                def _do():
                    try:
                        catalog.remove_organization(oid)
                        _success(f"Deleted '{oid}'.")
                    except CatalogError as exc:
                        _error(str(exc))
                return _do

            _delete_with_confirmation(f"del_org_{org.id}", org.id, _make_del_org())


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
    entries = sorted(catalog.list_entries(), key=lambda e: (e.en_US.name or "").lower())
    if not entries:
        st.info("No entries found.")
        return

    search = st.text_input("🔍 Filter by ID or name", key="entry_search")
    if search:
        s = search.lower()
        entries = [e for e in entries if s in e.id.lower() or s in e.en_US.name.lower()]

    for entry in entries:
        label = f"**{entry.en_US.name or '(no name)'}** ({entry.id})"
        with st.expander(label, expanded=False):
            _entry_edit_form(catalog, entry)


def _entry_edit_form(catalog: Catalog, entry: Entry) -> None:
    # --- Translation selector ---
    st.markdown("### Translations")
    existing_codes = entry.locale_codes()

    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_locale = st.text_input(
            "Add translation (locale code)",
            value="",
            key=f"edit_{entry.id}_new_locale",
            help="e.g. fr-FR, es-ES, ja-JP, nl-NL",
            placeholder="e.g. fr-FR",
        )
    with add_col2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("➕ Add", key=f"edit_{entry.id}_add_locale"):
            code = new_locale.strip()
            if code and code not in existing_codes:
                entry.locales[code] = EntryLocale(
                    name="", short_description="", long_description="",
                )
                st.rerun()
            elif code in existing_codes:
                _error(f"Translation '{code}' already exists.")

    selected_locale = st.selectbox(
        "Select translation to edit",
        existing_codes,
        key=f"edit_{entry.id}_locale_select",
    )

    with st.form(key=f"entry_edit_{entry.id}"):
        current_loc = entry.locale(selected_locale)
        st.markdown(f"### Translation: {selected_locale}")
        loc_fields = _entry_locale_fields(
            f"edit_{entry.id}_{selected_locale}", selected_locale, current_loc,
        )

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
            # Build updated locales: start from existing, update the selected one
            updated_locales = {}
            for code, loc in entry.locales.items():
                if code == selected_locale:
                    updated_locales[code] = EntryLocale(
                        name=loc_fields["name"],
                        short_description=loc_fields["short_description"],
                        long_description=loc_fields["long_description"],
                        keywords=loc_fields["keywords"],
                        icon=current_loc.icon,
                        links=current_loc.links,
                        tags=current_loc.tags,
                        visuals=current_loc.visuals,
                    )
                else:
                    updated_locales[code] = loc

            updated = Entry(
                id=entry.id,
                locales=updated_locales,
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

    def _do_delete_entry():
        try:
            catalog.remove_entry(entry.id)
            _success(f"Deleted '{entry.id}'.")
        except CatalogError as exc:
            _error(str(exc))

    _delete_with_confirmation(f"del_entry_{entry.id}", entry.id, _do_delete_entry)


def _entries_add(catalog: Catalog) -> None:
    org_options = _org_options(catalog, include_empty=True)
    org_labels = {o: _org_label(catalog, o) for o in org_options}
    cap_options = _def_options(catalog, "capabilities")
    art_options = _def_options(catalog, "artifacts")
    plat_options = _def_options(catalog, "platforms")
    prod_options = _def_options(catalog, "univention_products")

    # --- Manage locale list for new entry ---
    st.markdown("### Translations")
    if "new_entry_locales" not in st.session_state:
        st.session_state["new_entry_locales"] = list(REQUIRED_LOCALES)

    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_locale = st.text_input(
            "Add translation (locale code)",
            value="",
            key="new_entry_add_locale_input",
            help="e.g. fr-FR, es-ES, ja-JP, nl-NL",
            placeholder="e.g. fr-FR",
        )
    with add_col2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("➕ Add", key="new_entry_add_locale_btn"):
            code = new_locale.strip()
            if code and code not in st.session_state["new_entry_locales"]:
                st.session_state["new_entry_locales"].append(code)
                st.rerun()
            elif code in st.session_state["new_entry_locales"]:
                _error(f"Translation '{code}' already exists.")

    locale_codes = st.session_state["new_entry_locales"]

    with st.form(key="entry_add"):
        entry_id = st.text_input("Entry ID *", help="e.g. `COMMUNITY-my-app` or `UCSAPP-my-app`")
        version = st.text_input("Version", value="")

        locale_fields = {}
        for code in locale_codes:
            st.markdown(f"### Translation: {code}")
            locale_fields[code] = _entry_locale_fields(f"new_entry_{code}", code)

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
                locales = {}
                for code in locale_codes:
                    lf = locale_fields[code]
                    locales[code] = EntryLocale(
                        name=lf["name"],
                        short_description=lf["short_description"],
                        long_description=lf["long_description"],
                        keywords=lf["keywords"],
                    )
                new_entry = Entry(
                    id=entry_id.strip(),
                    locales=locales,
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
# Git helpers
# ---------------------------------------------------------------------------

def _git_run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd or CATALOG_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _git_is_repo() -> bool:
    """Check if the catalog root is inside a git repository."""
    result = _git_run("rev-parse", "--is-inside-work-tree")
    return result.returncode == 0


def _git_status_short() -> str:
    """Return ``git status --short`` output."""
    result = _git_run("status", "--short")
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_diff_stat() -> str:
    """Return ``git diff --stat`` (staged + unstaged) for display."""
    staged = _git_run("diff", "--cached", "--stat")
    unstaged = _git_run("diff", "--stat")
    parts = []
    if staged.stdout.strip():
        parts.append("**Staged:**\n```\n" + staged.stdout.strip() + "\n```")
    if unstaged.stdout.strip():
        parts.append("**Unstaged:**\n```\n" + unstaged.stdout.strip() + "\n```")
    return "\n\n".join(parts)


def _git_commit_and_push(message: str, push: bool) -> tuple[bool, str]:
    """Stage all changes, commit with *message*, and optionally push.

    Returns ``(success, detail_message)``.
    """
    add_result = _git_run("add", "--all")
    if add_result.returncode != 0:
        return False, f"git add failed: {add_result.stderr.strip()}"

    commit_result = _git_run("commit", "-m", message)
    if commit_result.returncode != 0:
        return False, f"git commit failed: {commit_result.stderr.strip()}"

    detail = commit_result.stdout.strip()

    if push:
        push_result = _git_run("push")
        if push_result.returncode != 0:
            return False, f"Committed, but git push failed: {push_result.stderr.strip()}"
        detail += "\n\nPushed to remote."

    return True, detail


def _sidebar_git() -> None:
    """Render the git status & commit section in the sidebar."""
    if not _git_is_repo():
        return

    st.divider()
    st.caption("Git")

    status = _git_status_short()
    if not status:
        st.info("Working tree clean — nothing to commit.")
        return

    st.markdown("**Changed files:**")
    st.code(status, language="")

    if st.button("📝 Commit changes …", key="git_commit_open"):
        st.session_state["_git_commit_dialog"] = True

    if st.session_state.get("_git_commit_dialog", False):
        diff_info = _git_diff_stat()
        if diff_info:
            st.markdown(diff_info)

        commit_msg = st.text_input(
            "Commit message *",
            key="git_commit_msg",
            placeholder="Describe your changes",
        )
        do_push = st.checkbox("Push after commit", key="git_push_checkbox")

        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("✅ Commit", key="git_commit_go", disabled=not commit_msg.strip()):
                ok, detail = _git_commit_and_push(commit_msg.strip(), do_push)
                st.session_state.pop("_git_commit_dialog", None)
                if ok:
                    _success(detail)
                else:
                    _error(detail)
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key="git_commit_cancel"):
                st.session_state.pop("_git_commit_dialog", None)
                st.rerun()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

_PAGES = {
    "📦 Entries": page_entries,
    "🏢 Organizations": page_organizations,
    "📐 Definitions": page_definitions,
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

        _sidebar_git()

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
