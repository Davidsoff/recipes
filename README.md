# Recepten

Persoonlijke verzameling van Cooklang-recepten. Elk recept is een `.cook` bestand met gestructureerde ingrediënten, keukengerei en stappen.

## Setup

Clone de repo:

```bash
git clone git@github.com:Davidsoff/recipes.git
cd recipes
```

### Pre-commit hook installeren

De pre-commit hook wordt **niet automatisch meegecloned** (`.git/hooks/` wordt niet door git bijgehouden). Installeer hem met:

```bash
# Optie 1: Symlink (aanbevolen)
ln -s ../../scripts/validate-recipes.py .git/hooks/pre-commit

# Optie 2: Git hooksPath (alternatief — werkt ook voor andere hooks in de repo)
git config core.hooksPath scripts/
```

Na installatie draait de hook automatisch bij elke `git commit` — hij valideert alle gestagede `.cook` bestanden en draait de unit tests.

### Vereisten

- **Python 3** (getest met 3.11+)
- **pytest** — `pip install pytest` (voor de unit tests)
- **cook CLI** — optioneel, alleen nodig voor recipe validatie. Volg de [officiële installatie-instructies](https://cooklang.org/cli/download/)

## Repo structuur

```
├── <recept>.cook          # Cooklang recipe file
├── scripts/
│   └── validate-recipes.py  # Pre-commit hook & validation script
├── tests/
│   └── test_validate_recipes.py
├── README.md
└── AGENTS.md
```

## Recept toevoegen

1. Maak een `.cook` bestand in de root van de repo
2. Zorg voor geldige YAML frontmatter met minimaal `title`, `servings`, `source` en `time`
3. Gebruik Cooklang syntax:
   - `@Ingrediënt{hoeveelheid%eenheid}` voor ingrediënten
   - `#Keukengerei` voor keukengerei
   - `-- Sectie --` voor stap-secties
4. Valideer: `python3 scripts/validate-recipes.py --all`
5. Commit (de pre-commit hook valideert automatisch)

## Voorbeeld

```cook
---
title: Spaghetti aglio e olio
time: 15 min
servings: 2
source: https://example.com/spaghetti-aglio-e-olio
cuisine: Italiaans
calories: 450 kcal
---

-- Ingrediënten (@2 personen) --
@Spaghetti{200%gr}
@Knoflookteen{4}
@Olijfolie{4%el}
@Peperoncino{1}
@Peterselie{handje}

-- Keukengerei --
#Pan
#Koekenpan

-- Stappen --
Kook de @Spaghetti{} beetgaar in gezouten water.

Verhit de @Olijfolie{} in een #Koekenpan{} en fruit de gesneden @Knoflookteen{} en @Peperoncino{}.

Meng de pasta door de olie en garneer met @Peterselie{}.
```

## Validation

De pre-commit hook (`scripts/validate-recipes.py`) controleert bij elke commit:

1. **Formatvalidatie** — `cook recipe` moet zonder fouten of waarschuwingen draaien
2. **Portie-aantal** — `servings:` in frontmatter moet een getal zijn
3. **Schaalbaarheid** — elk ingrediënt wordt geschaald naar 10 porties en de verhouding wordt gecontroleerd

Handmatig alle recepten controleren:

```bash
python3 scripts/validate-recipes.py --all
```

Tests draaien:

```bash
python3 -m pytest tests/ -v
```
