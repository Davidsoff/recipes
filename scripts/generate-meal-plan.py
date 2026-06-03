#!/usr/bin/env python3
"""
Weekly Dinner Meal Plan Generator
Generates a Cooklang .menu file for the upcoming week (Monday-Sunday)
Runs on Fridays at 20:00 to plan the next week's dinners.

Uses ISO week numbering for file naming and deterministic recipe rotation
based on the week number so each week gets a varied selection.

Recipes are organized by cuisine in subdirectories:
  italiaans/    → Italian(-American) recipes
  nederlands/   → Dutch recipes
  wereldkeuken/ → International recipes (Asian, African, American, etc.)
  overige/      → Non-dinner items (desserts, dough, etc.)
  meal-plans/   → Generated weekly .menu files
"""

import os
import re
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

REPO_DIR = os.path.expanduser("~/recipes-repo")
MENU_DIR = os.path.join(REPO_DIR, "meal-plans")

# Family size for scaling
SERVINGS = 4

# Recipes definitely NOT dinner material — matched on stem (filename without extension)
EXCLUDED_STEMS = {
    "kinderchocola-repen",   # dessert
    "ragusea-pizzadeeg",     # just dough
}

# Dietary notes for specific recipes
# Hard restriction: chicken egg (Joris)
# Soft: onion/leek (David — substitutes or omits)
# Soft: raw tomato (Maaike — cooked sauces fine)
DIETARY_INFO = {
    "bobotie-zonder-pakje": {"note": ""},
    "couscous-met-kip": {"note": ""},
    "kokossoep-met-udonnoedels-en-pindas": {"note": "Bevat ei — Joris: ei vervangen of weglaten"},
    "lasagne-bolognese": {"note": ""},
    "pasta-met-broccoli-en-spekreepjes": {"note": ""},
    "pasta-met-tuinerwten-en-spekreepjes": {"note": ""},
    "pasta-piselli": {"note": ""},
    "skillet-gnocchi-met-zalm-en-erwtjes": {"note": ""},
    "stamppotje-met-paprika-en-rucola": {"note": ""},
    "verstopte-groente-pastasaus": {"note": ""},
}


def get_iso_week():
    """Get the current ISO week number and year."""
    today = datetime.now()
    iso_year, iso_week, _ = today.isocalendar()
    return iso_year, iso_week


def get_next_monday():
    """Get next Monday's date (the start of the meal plan week)."""
    today = datetime.now()
    days_ahead = 0 - today.weekday()  # Monday = 0
    if days_ahead <= 0:  # Today is Monday or later in the week
        days_ahead += 7  # Next Monday
    return today + timedelta(days=days_ahead)


def get_dinner_recipes():
    """Get all dinner-appropriate .cook files with metadata.

    Searches recursively through all cuisine subdirectories.
    Returns a list of dicts with subdir info for menu file path generation.
    """
    recipes = []
    cook_dir = Path(REPO_DIR)

    for f in sorted(cook_dir.rglob("*.cook")):
        # Skip files in .git, scripts/, tests/, meal-plans/
        rel = f.relative_to(cook_dir)
        parts = rel.parts
        if len(parts) < 2:
            continue  # skip files in root
        subdir = parts[0]
        if subdir in (".git", "scripts", "tests", "meal-plans", "__pycache__"):
            continue

        stem = f.stem
        if stem in EXCLUDED_STEMS:
            continue

        content = f.read_text(encoding="utf-8")

        # Extract title from frontmatter
        title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else stem

        # Extract cuisine
        cuisine_match = re.search(r'^cuisine:\s*(.+)$', content, re.MULTILINE)
        cuisine = cuisine_match.group(1).strip().lower() if cuisine_match else "onbekend"

        # Extract servings
        servings_match = re.search(r'^servings:\s*(\d+)', content, re.MULTILINE)
        recipe_servings = int(servings_match.group(1)) if servings_match else 4

        # Scale factor
        scale_factor = round(SERVINGS / recipe_servings, 1)

        diet = DIETARY_INFO.get(stem, {"note": ""})

        recipes.append({
            "filename": f.name,
            "stem": stem,
            "subdir": subdir,
            "title": title,
            "cuisine": cuisine,
            "servings": recipe_servings,
            "scale": scale_factor,
            "note": diet["note"],
        })

    return recipes


def select_recipes(recipes, iso_week):
    """
    Select 7 recipes for the week using deterministic rotation.
    Uses the ISO week number as a seed to shuffle, then picks 7.
    """
    seed = str(iso_week)
    sorted_recipes = sorted(
        recipes,
        key=lambda r: hashlib.md5(f"{r['stem']}-{seed}".encode()).hexdigest()
    )

    # Pick 7, wrapping around if needed
    selected = []
    for i in range(7):
        idx = i % len(sorted_recipes)
        selected.append(sorted_recipes[idx])

    # Avoid consecutive same-cuisine nights
    for i in range(len(selected) - 1):
        if selected[i]["cuisine"] == selected[i + 1]["cuisine"]:
            for j in range(i + 2, len(selected)):
                if selected[j]["cuisine"] != selected[i]["cuisine"]:
                    selected[i + 1], selected[j] = selected[j], selected[i + 1]
                    break

    return selected


def generate_menu(recipes, iso_year, iso_week, next_monday):
    """Generate a Cooklang .menu file for the week's dinners."""
    week_dates = [next_monday + timedelta(days=i) for i in range(7)]
    dutch_days = [
        "Maandag", "Dinsdag", "Woensdag", "Donderdag",
        "Vrijdag", "Zaterdag", "Zondag"
    ]

    lines = []
    lines.append("---")
    lines.append(f"title: Weekmenu {iso_year}-Week {iso_week} (Avondeten)")
    lines.append(f"description: Avondmaaltijden voor de week van {next_monday.strftime('%d-%m-%Y')}")
    lines.append(f"servings: {SERVINGS}")
    lines.append("---")
    lines.append("")

    for i, (recipe, date) in enumerate(zip(recipes, week_dates)):
        lines.append(f"==Day {i}==")
        lines.append("")
        lines.append(f"-- {dutch_days[i]} {date.strftime('%d-%m-%Y')} --")
        lines.append("")

        if recipe["scale"] != 1.0:
            scale_str = f"{{{recipe['scale']}%servings}}"
        else:
            scale_str = f"{{{SERVINGS}%servings}}"

        # Recipe reference from meal-plans/ using subdirectory path
        recipe_path = f"../{recipe['subdir']}/{recipe['stem']}"
        lines.append("Dinner:")
        lines.append(f"- @{recipe_path}{scale_str}")
        lines.append("")

        if recipe["note"]:
            lines.append(f"-- {recipe['note']} --")
            lines.append("")

    content = "\n".join(lines)
    return content


def write_menu_file(content, iso_year, iso_week):
    """Write the .menu file to the meal-plans directory."""
    os.makedirs(MENU_DIR, exist_ok=True)
    filename = f"weekmenu-{iso_year}-W{iso_week:02d}.menu"
    filepath = os.path.join(MENU_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written: {filepath}")
    return filepath


def commit_and_push(filepath, iso_year, iso_week):
    """Commit and push the menu file to the repo."""
    os.chdir(REPO_DIR)
    os.system('git config user.email "david@soff.nl"')
    os.system('git config user.name "David Soff"')

    relpath = os.path.relpath(filepath, REPO_DIR)

    ret = os.system(f'git add "{relpath}"')
    if ret != 0:
        print("ERROR: git add failed")
        return False

    ret = os.system(f'git commit -m "feat: add weekmenu {iso_year}-W{iso_week:02d}"')
    if ret != 0:
        print("WARNING: git commit failed (maybe no changes?)")
        return False

    ret = os.system("git push origin main")
    if ret != 0:
        print("WARNING: git push failed")
        return False

    return True


def main():
    print("=== Weekly Dinner Meal Plan Generator ===")
    print(f"Time: {datetime.now().isoformat()}")

    iso_year, iso_week = get_iso_week()
    next_iso = get_next_monday().isocalendar()
    plan_year, plan_week = next_iso[0], next_iso[1]
    next_monday = get_next_monday()

    print(f"Planning week: {plan_year}-W{plan_week:02d} (starting {next_monday.strftime('%d-%m-%Y')})")

    recipes = get_dinner_recipes()
    print(f"Found {len(recipes)} dinner recipes")

    # Check if this week's menu already exists
    menu_filename = f"weekmenu-{plan_year}-W{plan_week:02d}.menu"
    menu_path = os.path.join(MENU_DIR, menu_filename)
    if os.path.exists(menu_path):
        print(f"Menu already exists: {menu_path}")
        print("Skipping generation.")
        return 0

    selected = select_recipes(recipes, plan_week)
    print("\nSelected dinners:")
    day_names_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, r in enumerate(selected):
        note_str = f" ⚠️ {r['note']}" if r['note'] else ""
        print(f"  {day_names_en[i]}: {r['title']} [{r['subdir']}] ({r['cuisine']}){note_str}")

    content = generate_menu(selected, plan_year, plan_week, next_monday)
    filepath = write_menu_file(content, plan_year, plan_week)

    print(f"\nMenu file written to: {filepath}")

    success = commit_and_push(filepath, plan_year, plan_week)
    if success:
        print("Committed and pushed successfully!")
    else:
        print("Commit/push had issues (see above).")

    print("\n" + "=" * 50)
    print(f"📋 Weekmenu {plan_year}-W{plan_week:02d} gegenereerd!")
    print(f"📁 {os.path.relpath(filepath, REPO_DIR)}")
    print("")
    day_names_nl = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    for i, r in enumerate(selected):
        note_str = f" ⚠️ {r['note']}" if r['note'] else ""
        print(f"  {day_names_nl[i]}: {r['title']}{note_str}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
