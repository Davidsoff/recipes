#!/usr/bin/env python3
"""Pre-commit hook: validate Cooklang recipes and check ingredient scaling.

Usage:
    python3 validate-recipes.py          # check staged .cook files only
    python3 validate-recipes.py --all    # check all .cook files
"""
import json
import os
import re
import subprocess
import sys

COOK = os.path.expanduser("~/.hermes/bin/cook")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


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


def get_numeric_display(display_str):
    """Extract the first numeric value from a display string like '2 el' or '1 1/4 c'."""
    m = re.match(r'([\d\s/.]+)', display_str)
    if not m:
        return None
    return frac_to_float(m.group(1).strip())


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
    # Extract YAML frontmatter between --- markers
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return None
    frontmatter = m.group(1)
    for line in frontmatter.split('\n'):
        if re.match(r'^servings\s*:', line, re.IGNORECASE):
            val = line.split(':', 1)[1].strip()
            try:
                return float(val)
            except ValueError:
                return None
    return None


def check_recipe(filepath):
    """Validate a single .cook file and check scaling. Returns list of error strings."""
    errors = []
    basename = os.path.basename(filepath)

    # Step 1: Validate format
    result = run([COOK, "recipe", filepath])
    if result.returncode != 0:
        errors.append(f"  ✖  {basename}: validation FAILED\n     {result.stdout[:300]}{result.stderr[:300]}")
        return errors

    # Check for warnings
    if re.search(r'warn', result.stdout, re.IGNORECASE):
        warn_lines = [l for l in result.stdout.split('\n') if 'warn' in l.lower()]
        for w in warn_lines[:3]:
            errors.append(f"  ⚠  {basename}: {w.strip()}")
        if errors:
            return errors

    # Step 2: Parse servings
    servings = get_servings(filepath)
    if servings is None:
        errors.append(f"  ⚠  {basename}: no numeric servings field — skipping scale check")
        return errors

    if servings <= 0:
        errors.append(f"  ⚠  {basename}: invalid servings ({servings}) — skipping scale check")
        return errors

    # Step 3: Scale to 10 servings
    factor = 10.0 / servings
    result_scaled = run([COOK, "recipe", f"{filepath}:{factor}"])
    if result_scaled.returncode != 0:
        errors.append(f"  ✖  {basename}: scaling to 10 servings FAILED (×{factor})")
        return errors

    # Step 4: Compare ingredient amounts
    orig_ings = parse_ingredients(result.stdout)
    scaled_ings = parse_ingredients(result_scaled.stdout)

    if len(orig_ings) != len(scaled_ings):
        errors.append(f"  ⚠  {basename}: ingredient count mismatch ({len(orig_ings)} → {len(scaled_ings)})")

    for i, (o_name, o_disp) in enumerate(orig_ings):
        if i >= len(scaled_ings):
            break
        s_name, s_disp = scaled_ings[i]

        o_num = get_numeric_display(o_disp)
        s_num = get_numeric_display(s_disp)

        if o_num is not None and s_num is not None:
            if abs(o_num - s_num) < 0.001:
                errors.append(f"  ✖  {basename}: '{o_name}' unchanged ({o_disp} → {s_disp})")
            elif s_num == 0 and o_num > 0:
                errors.append(f"  ✖  {basename}: '{o_name}' collapsed to zero ({o_disp} → {s_disp})")

    return errors


def main():
    # Determine which files to check
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        files = sorted([
            os.path.join(REPO_DIR, f)
            for f in os.listdir(REPO_DIR)
            if f.endswith('.cook')
        ])
    else:
        # Staged files only
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
        return 0

    all_errors = []
    for filepath in files:
        basename = os.path.basename(filepath)
        print(f"\n  ── {basename} ──")
        errors = check_recipe(filepath)
        if errors:
            all_errors.extend(errors)
            for e in errors:
                print(e)
        else:
            print("  ✓  Format valid, servings parse, scaling OK, all ingredients scale")

    print()
    if all_errors:
        print(f"  ✖  {len(all_errors)} error(s) found. Fix before committing.")
        return 1
    else:
        print(f"  ✓  All {len(files)} recipe(s) valid and scale correctly.")
        return 0


if __name__ == "__main__":
    sys.exit(main())