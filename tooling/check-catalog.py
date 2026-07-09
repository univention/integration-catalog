#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH

"""
Consistency checker for the Univention Nubus Integration Catalog.

Loads the catalog using the integration_catalog library and verifies that all
entries reference only existing capabilities, organizations, products,
platforms, artifacts, and technologies.

Exits with code 0 if all entries are consistent, 1 if issues are found.

Usage:
    # With the editor venv activated:
    source editor/integration_catalog/.venv/bin/activate
    python tooling/check-catalog.py

    # Without installing the package (library loaded from source tree):
    python tooling/check-catalog.py

    # Against a different catalog root:
    python tooling/check-catalog.py --root /path/to/catalog
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Fall back to the in-tree source when the package is not installed.
_LIBRARY_SRC = Path(__file__).resolve().parent.parent / "editor" / "integration_catalog" / "src"
if _LIBRARY_SRC.is_dir():
    sys.path.insert(0, str(_LIBRARY_SRC))

try:
    from integration_catalog import Catalog
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
except ImportError as exc:
    print(
        f"Import error: {exc}\n"
        "Activate the venv:  source editor/integration_catalog/.venv/bin/activate\n"
        "or install the package:  pip install -e editor/integration_catalog",
        file=sys.stderr,
    )
    sys.exit(2)


def _check_entries(catalog) -> list[str]:
    """Additional per-entry checks beyond reference validation."""
    errors: list[str] = []
    for entry_id, entry in catalog.entries.items():
        meta = entry.metadata
        ts = entry.technical_specifications

        if not meta.created_by.strip():
            errors.append(f"Entry '{entry_id}': metadata.created_by must be set.")

        if not meta.creation_date.strip():
            errors.append(f"Entry '{entry_id}': metadata.creation_date must be set.")

        if not meta.last_update_date.strip():
            errors.append(f"Entry '{entry_id}': metadata.last_update_date must be set.")
        elif entry.path and entry.path.exists():
            try:
                last_update = date.fromisoformat(meta.last_update_date)
                file_mtime = date.fromtimestamp(entry.path.stat().st_mtime)
                if file_mtime - last_update > timedelta(days=1):
                    errors.append(
                        f"Entry '{entry_id}': last_update_date '{last_update}' is more than "
                        f"one day older than the file modification date '{file_mtime}'."
                    )
            except ValueError:
                errors.append(
                    f"Entry '{entry_id}': last_update_date '{meta.last_update_date}' "
                    f"is not a valid ISO date."
                )

        if not ts.capabilities:
            errors.append(f"Entry '{entry_id}': capabilities must have at least one entry.")

        if not ts.compatible_products:
            errors.append(f"Entry '{entry_id}': compatible_products must have at least one entry.")

        if not ts.compatible_platforms:
            errors.append(f"Entry '{entry_id}': compatible_platforms must have at least one entry.")

        if not ts.artifacts:
            errors.append(f"Entry '{entry_id}': artifacts must have at least one entry.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check consistency of all integration catalog entries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        metavar="PATH",
        help="Catalog root directory (default: repo root relative to this script)",
    )
    cli_args = parser.parse_args()

    console = Console()
    root = Path(cli_args.root).resolve()

    console.print(f"Catalog root: [cyan]{root}[/]")

    catalog = Catalog.load(root)

    # ── summary table ────────────────────────────────────────────────────────
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2, 0, 0))
    table.add_column("Collection")
    table.add_column("Count", justify="right")

    table.add_row("entries", str(len(catalog.entries)))
    table.add_row("organizations", str(len(catalog.organizations)))
    for dtype, df in sorted(catalog.definitions.items()):
        table.add_row(f"  {dtype}", str(len(df.items)))

    console.print(table)
    console.print()

    # ── run checks ───────────────────────────────────────────────────────────
    console.print("Running consistency checks…")
    errors = catalog.load_errors + catalog.validate() + _check_entries(catalog)

    if not errors:
        console.print(
            f"\n[bold green]✓ All {len(catalog.entries)} entries are consistent.[/]"
        )
        return 0

    console.print(
        f"\n[bold red]✗ Found {len(errors)} issue(s):[/]\n"
    )
    for i, error in enumerate(errors, 1):
        console.print(f"  [red]{i:3d}.[/] {error}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
