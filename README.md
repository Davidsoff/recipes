# Recepten

Persoonlijke verzameling van Cooklang-recepten. Elk recept is een `.cook` bestand met gestructureerde ingrediënten, keukengerei en stappen.

## Structuur

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
