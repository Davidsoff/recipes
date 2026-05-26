#!/usr/bin/env bash
# pre-commit hook: validate Cooklang recipes and check scaling to 10 servings
set -euo pipefail

COOK="${HOME}/.hermes/bin/cook"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HAS_ERRORS=0

# Process only staged .cook files, or all if called directly
if [ "${1:-}" = "--all" ]; then
    FILES=$(find "$REPO_DIR" -maxdepth 1 -name '*.cook' | sort)
else
    FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.cook$' || true)
fi

if [ -z "$FILES" ]; then
    echo "  ✓ No .cook files to check"
    exit 0
fi

for file in $FILES; do
    [[ -f "$file" ]] || file="${REPO_DIR}/${file}"
    [[ -f "$file" ]] || continue

    BASENAME=$(basename "$file")
    echo ""
    echo "  ── Checking: ${BASENAME} ──"

    # Step 1: Validate recipe format
    VALID_OUTPUT=$("$COOK" recipe "$file" 2>&1) && VALID_OK=true || VALID_OK=false

    if [ "$VALID_OK" = false ]; then
        echo "  ✖  Validation FAILED"
        echo "     $VALID_OUTPUT" | head -5
        HAS_ERRORS=1
        continue
    fi

    # Check for warnings in output
    if echo "$VALID_OUTPUT" | grep -qi 'warn'; then
        WARN_LINE=$(echo "$VALID_OUTPUT" | grep -i 'warn' | head -1)
        echo "  ⚠  Warning: $WARN_LINE"
        HAS_ERRORS=1
        continue
    fi

    echo "  ✓  Format valid"

    # Step 2: Parse servings from YAML frontmatter
    SERVINGS=$(sed -n '/^---$/,/^---$/p' "$file" | grep -i '^servings:' | head -1 | sed 's/.*:[[:space:]]*//' | tr -d ' ')
    if [ -z "$SERVINGS" ]; then
        echo "  ⚠  No servings field found — skipping scale check"
        HAS_ERRORS=1
        continue
    fi

    # Handle fractional servings (e.g. 0.5)
    if ! echo "$SERVINGS" | grep -qE '^[0-9]+(\.[0-9]+)?$'; then
        echo "  ⚠  Non-numeric servings '$SERVINGS' — skipping scale check"
        continue
    fi

    echo "  ✓  Servings: $SERVINGS"

    # Step 3: Scale to 10 servings
    FACTOR=$(echo "scale=4; 10 / $SERVINGS" | bc 2>/dev/null || python3 -c "print(10 / $SERVINGS)" 2>/dev/null || echo "")

    if [ -z "$FACTOR" ]; then
        echo "  ⚠  Could not compute scale factor — skipping scale check"
        HAS_ERRORS=1
        continue
    fi

    if ! SCALED_OUTPUT=$("$COOK" recipe "${file}:${FACTOR}" 2>&1); then
        echo "  ✖  Scaling to 10 servings FAILED (factor ×${FACTOR})"
        echo "     $SCALED_OUTPUT" | head -5
        HAS_ERRORS=1
        continue
    fi

    # Quick sanity: check scaled servings display
    SCALED_SERVINGS=$(echo "$SCALED_OUTPUT" | grep -i '^servings:' | head -1 | sed 's/.*:[[:space:]]*//')
    echo "  ✓  Scales to $SCALED_SERVINGS servings (×${FACTOR})"
done

echo ""
if [ "$HAS_ERRORS" -ne 0 ]; then
    echo "  ✖  Some recipes failed validation. Fix errors before committing."
    exit 1
fi

echo "  ✓  All recipes valid and scale correctly."
exit 0