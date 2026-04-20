#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Univention GmbH
#
# Launch the Integration Catalog UI editor.
# Run this script from any directory; it resolves paths automatically.
#
# Usage:
#   ./start-ui.sh                        # uses the parent directory as catalog root
#   ./start-ui.sh --root /path/to/catalog

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
UI_MODULE="${SCRIPT_DIR}/src/integration_catalog/ui.py"

# Default catalog root: two levels up from the editor directory
CATALOG_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Parse --root argument if provided
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --root|-r)
            CATALOG_ROOT="$(cd "$2" && pwd)"
            shift 2
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

# --- First-time setup: create venv and install if missing ---
if [[ ! -f "${VENV_DIR}/bin/streamlit" ]]; then
    echo "🔧 First-time setup: creating virtual environment..."
    python3 -m venv "${VENV_DIR}"
    echo "📦 Installing dependencies (this takes a moment)..."
    "${VENV_DIR}/bin/pip" install --quiet -e "${SCRIPT_DIR}"
    echo "✅ Setup complete."
fi

echo "🚀 Starting Integration Catalog Editor..."
echo "   Catalog root: ${CATALOG_ROOT}"
echo "   Open http://localhost:8501 in your browser (opens automatically)."
echo "   Press Ctrl+C to stop."
echo ""

"${VENV_DIR}/bin/streamlit" run "${UI_MODULE}" \
    --server.headless false \
    --browser.gatherUsageStats false \
    -- --root "${CATALOG_ROOT}" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
