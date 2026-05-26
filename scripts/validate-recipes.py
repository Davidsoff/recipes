#!/usr/bin/env python3
"""Pre-commit hook: validate Cooklang recipes and verify ingredient scaling.

Checks every staged .cook file for:
1. Format validity (cook recipe must exit 0, no warnings)
2. Numeric servings field in YAML frontmatter
3. Correct scaling of all ingredients to 10 servings

Usage:
    python3 validate-recipes.py          # check staged .cook files only
    python3 validate-recipes.py --all    # check all .cook files in repo
"""
import os
import re
import subprocess
import sys

COOK = os.path.expanduser("~/.hermes/bin/cook")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Unit conversion to grams (for mass) or millilitres (for volume)
# (base_grams_or_ml, category) — "mass" or "volume"
UNIT_BASE = {
    "g": (1, "mass"),
    "gr": (1, "mass"),
    "gram": (1, "mass"),
    "kg": (1000, "mass"),
    "kilo": (1000, "mass"),
    "ml": (1, "volume"),
    "milliliter": (1, "volume"),
    "l": (1000, "volume"),
    "liter": (1000, "volume"),
    "oz": (28.35, "mass"),
    "ounce": (28.35, "mass"),
    "lb": (453.6, "mass"),
    "pound": (453.6, "mass"),
}


def run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return result


def frac_to_float(s):
    """Convert '1/2', '1 1/4', '0.5', '3' etc to float. Returns None on failure."""
    s = s.strip()
    if not s:
        return None
    try:
        parts = s.split()
        total = 0.0
        for part in parts:
            if '/' in part:
                num, den = part.split('/')
                total += float(num) / float(den)
            else:
                total += float(part)
        return total
    except (ValueError, ZeroDivisionError):
        return None


def parse_display(display_str):
    """Parse a display string like '2 el' or '1 1/4 c' into (numeric_value, unit_string).

    Returns (float|None, str).  The unit string is the remainder after the number.
    """
    m = re.match(r'([\d\s/.]+)\s*(.*)', display_str)
    if not m:
        return None, display_str
    num = frac_to_float(m.group(1))
    unit = m.group(2).strip()
    return num, unit


def convert_to_base(num, unit_str):
    """Convert (num, unit_str) to a common base (grams or ml).

    Returns (base_value, category) where category is 'mass', 'volume', or 'count'.
    For countable items (stuks, groot, el, tl, etc.) the raw number is returned.
    """
    if not unit_str:
        return num, "count"

    # Extract the primary unit word (first word, ignoring parentheticals)
    unit_word = unit_str.split()[0].lower().rstrip(".,;")

    # Countable / non-convertible units
    countable = {
        "stuks", "stuk", "groot", "grote", "stengels", "stengel",
        "handje", "blikje", "blik", "teen", "tenen", "bol", "bollen",
        "el", "eetlepel", "tl", "theelepel",
        "c", "cup", "cups", "koppen", "kop",
        "pound", "pounds",
        "naar",  # "naar smaak"
    }
    if unit_word in countable:
        return num, "count"

    # Convertible units
    if unit_word in UNIT_BASE:
        multiplier, category = UNIT_BASE[unit_word]
        return num * multiplier, category

    # Unknown — treat as countable
    return num, "count"


def parse_ingredients(text):
    """Parse human-readable cook recipe output into list of (name, display_string)."""
    lines = text.split('\n')
    ings = []
    in_ings = False
    for line in lines:
        if line.strip() == 'Ingredients:':
            in_ings = True
            continue
        if in_ings:
            if line.strip().startswith('Cookware:') or line.strip().startswith('Steps:'):
                break
            m = re.match(r'  (.+?)\s{2,}(.+?)\s*$', line)
            if m:
                name = m.group(1).strip()
                display = m.group(2).strip()
                if name:
                    ings.append((name, display))
    return ings


def get_servings(filepath):
    """Parse servings from YAML frontmatter."""
    with open(filepath) as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).split('\n'):
        if re.match(r'^servings\s*:', line, re.IGNORECASE):
            val = line.split(':', 1)[1].strip()
            try:
                return float(val)
            except ValueError:
                return None
    return None


def check_recipe(filepath):
    """Validate a single .cook file and check ingredient scaling. Returns list of error strings."""
    errors = []
    basename = os.path.basename(filepath)

    # Step 1: Validate format
    result = run([COOK, "recipe", filepath])
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[:200]
        errors.append(f"  ✖  {basename}: validation FAILED\n     {tail}")
        return errors

    # Check for warnings
    if re.search(r'warn', result.stdout, re.IGNORECASE):
        warn_lines = [l for l in result.stdout.split('\n') if 'warn' in l.lower()]
        for w in warn_lines[:3]:
            errors.append(f"  ⚠  {basename}: {w.strip()}")
        return errors  # warnings = hard fail

    # Step 2: Parse servings
    servings = get_servings(filepath)
    if servings is None:
        errors.append(f"  ⚠  {basename}: no numeric servings in frontmatter — can't verify scaling")
        return errors
    if servings <= 0:
        errors.append(f"  ⚠  {basename}: invalid servings ({servings})")
        return errors

    # Step 3: Scale to 10 servings
    factor = 10.0 / servings
    result_scaled = run([COOK, "recipe", f"{filepath}:{factor}"])
    if result_scaled.returncode != 0:
        errors.append(f"  ✖  {basename}: scaling to 10 servings FAILED (×{factor})")
        return errors

    # Step 4: Verify scaling ratio for every ingredient
    orig_ings = parse_ingredients(result.stdout)
    scaled_ings = parse_ingredients(result_scaled.stdout)

    if len(orig_ings) != len(scaled_ings):
        errors.append(f"  ⚠  {basename}: ingredient count mismatch ({len(orig_ings)} → {len(scaled_ings)})")

    for i, (o_name, o_disp) in enumerate(orig_ings):
        if i >= len(scaled_ings):
            break

        s_name, s_disp = scaled_ings[i]
        o_num, o_unit = parse_display(o_disp)
        s_num, s_unit = parse_display(s_disp)

        if o_num is None or s_num is None:
            continue  # non-numeric (e.g. "naar smaak")

        # Convert both to base units
        o_base, o_cat = convert_to_base(o_num, o_unit)
        s_base, s_cat = convert_to_base(s_num, s_unit)

        # Check the ratio
        if o_cat != "count" and o_cat == s_cat and o_cat in ("mass", "volume") and o_base > 0:
            # Both in same base category (mass or volume) — precise ratio check
            expected_base = o_base * factor
            ratio = s_base / expected_base
            if abs(ratio - 1.0) > 0.05:
                errors.append(
                    f"  ✖  {basename}: '{o_name}' wrong scale "
                    f"({o_disp} → {s_disp}, expected ×{factor} but got ×{ratio:.4f})"
                )
        elif o_num > 0:
            # Countable items — approximate check
            expected_approx = o_num * factor
            ratio = s_num / expected_approx if expected_approx > 0 else 0
            if abs(ratio - 1.0) > 0.15:
                errors.append(
                    f"  ✖  {basename}: '{o_name}' wrong scale "
                    f"({o_disp} → {s_disp}, expected ×{factor} but got ×{ratio:.4f})"
                )

    return errors


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        files = sorted([
            os.path.join(REPO_DIR, f)
            for f in os.listdir(REPO_DIR)
            if f.endswith('.cook')
        ])
    else:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, cwd=REPO_DIR
        )
        files = [
            os.path.join(REPO_DIR, f) if not os.path.isabs(f) else f
            for f in result.stdout.strip().split('\n')
            if f.endswith('.cook') and os.path.exists(
                os.path.join(REPO_DIR, f) if not os.path.isabs(f) else f
            )
        ]

    if not files:
        print("  ✓ No .cook files to check")
        recipe_ok = True
    else:
        recipe_ok = True
        all_errors = []
        for filepath in files:
            basename = os.path.basename(filepath)
            print(f"\n  ── {basename} ──")
            errors = check_recipe(filepath)
            if errors:
                all_errors.extend(errors)
                for e in errors:
                    print(e)
                recipe_ok = False
            else:
                print("  ✓  Format valid, servings parse, scaling OK, all ingredients scale correctly")

        if not recipe_ok:
            print(f"\n  ✖  {len(all_errors)} error(s) in recipe validation.")
            return 1

        print(f"\n  ✓  All {len(files)} recipe(s) valid and scale correctly.")

    # Step 5: Run unit tests
    print("\n  ── Running unit tests ──")
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    # Print test output inline (strip trailing whitespace for clean display)
    for line in test_result.stdout.split('\n'):
        print(f"  {line.rstrip()}")
    if test_result.stderr.strip():
        for line in test_result.stderr.split('\n'):
            print(f"  {line.rstrip()}")

    if test_result.returncode != 0:
        print("  ✖  Unit tests FAILED. Fix before committing.")
        return 1
    else:
        print("  ✓  Unit tests pass.")

    return 0


if __name__ == "__main__":
    sys.exit(main())