#!/bin/bash
# Neutral quality gate script
#
# Reads a manifest of quality check files and verifies they exist and are not empty.
# The manifest is expected to be a README.md file in the target directory,
# with each check file referenced in a line like:
# 1. `my-check.md` - A description of the check.

set -euo pipefail

# Use the directory provided as the first argument, or default to the canonical location.
CHECKS_DIR="${1:-docs/quality/review-checks}"
MANIFEST_FILE="${CHECKS_DIR}/README.md"

if [ ! -f "${MANIFEST_FILE}" ]; then
    echo "ERROR: Quality gate manifest not found at ${MANIFEST_FILE}" >&2
    exit 1
fi

# Extract filenames from lines containing backticked filenames.
# We accept two manifest styles the docs use interchangeably:
#   - Markdown numbered list:  1. `acceptance-criteria.md` - ...
#   - Markdown table row:      | 1. | `acceptance-criteria.md` | ...
# The pattern below matches an optional leading table pipe, then a numbered
# list marker, so both styles are picked up. The backticked filename is then
# pulled out of whatever matched.
check_files=$(grep -E '^[[:space:]]*\|?[[:space:]]*[0-9]+\.' "${MANIFEST_FILE}" | grep -o '`[^`]*`' | sed 's/`//g')

if [ -z "${check_files}" ]; then
    echo "ERROR: No quality check files found in manifest: ${MANIFEST_FILE}" >&2
    exit 1
fi

# Loop through the discovered check files and validate them.
for check_file in $check_files; do
    full_path="${CHECKS_DIR}/${check_file}"

    if [ ! -f "${full_path}" ]; then
        echo "ERROR: Quality check file not found: ${full_path}" >&2
        exit 1
    fi

    if [ ! -s "${full_path}" ]; then
        echo "ERROR: Quality check file is empty: ${full_path}" >&2
        exit 1
    fi
done

echo "All quality checks passed in ${CHECKS_DIR}."
exit 0
