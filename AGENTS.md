# AGENTS.md — Recipes Repo

This file contains instructions for AI coding agents working with this repository.

## Repository Structure

```
~/recipes-repo/                   # Clone of github.com/Davidsoff/recipes
├── italiaans/                    # Italian & Italian-American recipes
│   ├── lasagne-bolognese.cook
│   ├── pasta-piselli.cook
│   └── verstopte-groente-pastasaus.cook
├── nederlands/                   # Dutch recipes
│   ├── pasta-met-broccoli-en-spekreepjes.cook
│   ├── pasta-met-tuinerwten-en-spekreepjes.cook
│   └── stamppotje-met-paprika-en-rucola.cook
├── wereldkeuken/                 # International recipes
│   ├── bobotie-zonder-pakje.cook
│   ├── couscous-met-kip.cook
│   ├── kokossoep-met-udonnoedels-en-pindas.cook
│   └── skillet-gnocchi-met-zalm-en-erwtjes.cook
├── overige/                      # Non-dinner items (desserts, dough, etc.)
│   ├── kinderchocola-repen.cook
│   └── ragusea-pizzadeeg.cook
├── meal-plans/                   # Generated weekly .menu files
│   └── weekmenu-YYYY-Www.menu
├── scripts/
│   ├── generate-meal-plan.py     # Weekly meal plan generator
│   └── validate-recipes.py       # Pre-commit hook and validation script
├── tests/
│   └── test_validate_recipes.py  # Unit tests for the validator
├── README.md
└── AGENTS.md                     # This file
```

## How Recipes Are Added

This repo is populated by an AI agent (Hermes) that processes recipe URLs sent via Telegram.

### Recipe Pipeline

1. User sends a recipe URL via Telegram DM
2. Extract structured data using `cook import --skip-conversion <URL>`
3. If that fails, use browser fallback (JSON-LD extraction or DOM scraping)
4. **Always translate English recipes to full Dutch** — title, description, ingredients, and instructions. If the recipe is already in Dutch (e.g. from leukerecepten.nl, ohmyfoodness.nl), no translation needed.
5. Write the `.cook` file to `/tmp/` first
6. Validate with `cook recipe /tmp/<file>.cook` — fix any warnings or errors
7. Determine the correct cuisine subdirectory from the `cuisine:` field in YAML frontmatter:
   - `italiaans` / `Italiaans` → `italiaans/`
   - `nederlands` / `Nederlands` → `nederlands/`
   - Everything else → `wereldkeuken/`
   - Non-dinner items → `overige/`
8. Copy to `~/recipes-repo/<subdirectory>/`
9. Commit with message: `feat: add <recipe name in Dutch>`
10. Push

### Commit Conventions

- One commit per recipe: `feat: add <dutch name>`
- Fix commits: `fix: <what was fixed>`
- Use lowercase, no trailing period

### Cooklang Format Rules

Every `.cook` file must have:

**YAML frontmatter:**
```yaml
---
title: Dutch Recipe Name
description: Short Dutch description
time: X min
servings: X
source: <original URL>
cuisine: <country in Dutch, e.g. Italiaans, Marokkaans>
calories: ~X kcal
---
```

**Ingredients** — use `@Ingredient{amount%unit}` syntax:
```cook
-- Ingrediënten (@X personen) --
@Rundergehakt{500%gr}
@Ui{1}
@Knoflookteen{2}
```

**Cookware** — use `#Cookware` syntax:
```cook
-- Keukengerei --
#Ovenschaal
#Koekenpan
```

**Steps** — use `-- Stappen --` section headers, reference ingredients inline:
```cook
-- Stappen --
Fruit de gesnipperde @Ui{} en @Knoflookteen{} in de @Olijfolie{}.
Voeg het @Rundergehakt{} toe en bak rul.
```

### Time Format

Use total minutes only: `time: 45 min`, `time: 105 min`. Do NOT use `1u45` or `1h45` — these trigger warnings from `cook recipe`.

### Serving Formats

Always use a plain number: `servings: 4`. Do NOT use ranges (`4-6 porties`) or text (`4 people`).

### Validation Requirements

- Every recipe MUST pass `cook recipe <file>` without warnings or errors before committing
- Every recipe MUST scale correctly to 10 servings (checked by pre-commit hook)
- Pre-commit hook at `.git/hooks/pre-commit` runs automatically
- Run full validation with: `python3 scripts/validate-recipes.py --all`
- Run tests with: `python3 -m pytest tests/ -v`

### General Agent Guidelines

- **English conversation** with the user unless explicitly asked to use Dutch
- **Full Dutch recipes** — title, description, ingredients, and instructions all in Dutch
- **Preserve source URL** in frontmatter
- **One commit per recipe**, push to `main` via SSH deploy key