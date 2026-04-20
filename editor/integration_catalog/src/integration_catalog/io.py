# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""YAML I/O helpers for the integration catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_SPDX_HEADER = (
    "# SPDX-License-Identifier: AGPL-3.0-only\n"
    "# SPDX-FileCopyrightText: 2026 Univention GmbH\n\n"
)


class _LiteralStr(str):
    """Marker for strings that should be dumped as YAML literal blocks (|)."""


def _literal_representer(dumper: yaml.Dumper, data: _LiteralStr) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """Use literal block style for multi-line strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class _CatalogDumper(yaml.Dumper):
    pass


_CatalogDumper.add_representer(str, _str_representer)
_CatalogDumper.add_representer(_LiteralStr, _literal_representer)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its content as a dict."""
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def save_yaml(path: Path, data: dict[str, Any], header_comment: str = "") -> None:
    """Write *data* as YAML to *path*, prepending optional comment lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(
        data,
        Dumper=_CatalogDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    header = _SPDX_HEADER
    if header_comment:
        header += header_comment + "\n\n"
    with path.open("w", encoding="utf-8") as fh:
        fh.write(header + content)
