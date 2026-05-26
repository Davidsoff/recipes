"""Unit tests for scripts/validate-recipes.py.

Tests all pure functions (no cook CLI dependency) via pytest.
Run with: python3 -m pytest tests/ -v
"""
import os
import sys
import tempfile
import textwrap

# Import from scripts/validate_recipes.py via path manipulation
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(_SCRIPT_DIR, "scripts"))
sys.path.insert(0, _SCRIPT_DIR)  # also for relative discovery via pytest

# We use importlib to avoid PYTHONDONTWRITEBYTECODE and __pycache__ conflicts
import importlib.util
spec = importlib.util.spec_from_file_location(
    "validate_recipes",
    os.path.join(_SCRIPT_DIR, "scripts", "validate-recipes.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

frac_to_float = mod.frac_to_float
parse_display = mod.parse_display
convert_to_base = mod.convert_to_base
parse_ingredients = mod.parse_ingredients
get_servings = mod.get_servings


# ─── frac_to_float ────────────────────────────────────────────────────────────


class TestFracToFloat:
    def test_simple_integer(self):
        assert frac_to_float("3") == 3.0

    def test_decimal(self):
        assert frac_to_float("2.5") == 2.5

    def test_simple_fraction(self):
        assert frac_to_float("1/2") == 0.5

    def test_mixed_fraction(self):
        assert frac_to_float("1 1/4") == 1.25

    def test_three_part_fraction(self):
        assert frac_to_float("2 3/4") == 2.75

    def test_empty_string(self):
        assert frac_to_float("") is None

    def test_whitespace_only(self):
        assert frac_to_float("   ") is None

    def test_invalid_string(self):
        assert frac_to_float("abc") is None

    def test_division_by_zero(self):
        assert frac_to_float("1/0") is None

    def test_trailing_whitespace(self):
        assert frac_to_float("  1/2  ") == 0.5

    def test_large_number(self):
        assert frac_to_float("500") == 500.0


# ─── parse_display ────────────────────────────────────────────────────────────


class TestParseDisplay:
    def test_simple_unit(self):
        num, unit = parse_display("2 el")
        assert num == 2.0
        assert unit == "el"

    def test_fraction_with_unit(self):
        num, unit = parse_display("1/2 c")
        assert num == 0.5
        assert unit == "c"

    def test_mixed_fraction_with_unit(self):
        num, unit = parse_display("1 1/4 c")
        assert num == 1.25
        assert unit == "c"

    def test_no_unit(self):
        num, unit = parse_display("3")
        assert num == 3.0
        assert unit == ""

    def test_naar_smaak(self):
        num, unit = parse_display("naar smaak")
        assert num is None

    def test_unit_with_parenthetical(self):
        num, unit = parse_display("2 stuks (groot)")
        assert num == 2.0
        assert unit == "stuks (groot)"

    def test_decimal_with_unit(self):
        num, unit = parse_display("312.5 g")
        assert num == 312.5
        assert unit == "g"

    def test_non_numeric(self):
        num, unit = parse_display("abc")
        assert num is None


# ─── convert_to_base ──────────────────────────────────────────────────────────


class TestConvertToBase:
    def test_grams(self):
        val, cat = convert_to_base(400, "g")
        assert val == 400
        assert cat == "mass"

    def test_kilograms(self):
        val, cat = convert_to_base(1, "kg")
        assert val == 1000
        assert cat == "mass"

    def test_millilitres(self):
        val, cat = convert_to_base(300, "ml")
        assert val == 300
        assert cat == "volume"

    def test_litres(self):
        val, cat = convert_to_base(1.5, "l")
        assert val == 1500
        assert cat == "volume"

    def test_ounces(self):
        val, cat = convert_to_base(1, "oz")
        assert val == 28.35
        assert cat == "mass"

    def test_pounds(self):
        val, cat = convert_to_base(1, "lb")
        assert val == 453.6
        assert cat == "mass"

    def test_countable_stuks(self):
        val, cat = convert_to_base(2, "stuks")
        assert val == 2
        assert cat == "count"

    def test_countable_el(self):
        val, cat = convert_to_base(3, "el")
        assert val == 3
        assert cat == "count"

    def test_countable_tl(self):
        val, cat = convert_to_base(1.5, "tl")
        assert val == 1.5
        assert cat == "count"

    def test_no_unit(self):
        val, cat = convert_to_base(2.5, "")
        assert val == 2.5
        assert cat == "count"

    def test_naar_smaak(self):
        val, cat = convert_to_base(0, "naar smaak")
        assert val == 0
        assert cat == "count"

    def test_unknown_unit(self):
        val, cat = convert_to_base(1, "furlong")
        assert val == 1
        assert cat == "count"

    def test_gr_variant(self):
        val, cat = convert_to_base(200, "gr")
        assert val == 200
        assert cat == "mass"


# ─── parse_ingredients ────────────────────────────────────────────────────────


class TestParseIngredients:
    def test_basic_ingredients(self):
        text = textwrap.dedent("""\
            Ingredients:
              Olijfolie                2 el
              Ui                       1 stuks
              Wortel                   400 gr
              Peper en zout            naar smaak
            Cookware:
              Pan
        """)
        ings = parse_ingredients(text)
        assert len(ings) == 4
        assert ings[0] == ("Olijfolie", "2 el")
        assert ings[1] == ("Ui", "1 stuks")
        assert ings[2] == ("Wortel", "400 gr")
        assert ings[3] == ("Peper en zout", "naar smaak")

    def test_no_ingredients_section(self):
        ings = parse_ingredients("Some random text\nwithout ingredients")
        assert ings == []

    def test_empty_ingredients(self):
        text = textwrap.dedent("""\
            Recipe Name
            Ingredients:
            Cookware:
        """)
        ings = parse_ingredients(text)
        assert ings == []

    def test_with_metadata_header(self):
        """Full cook recipe output with source, time, servings header."""
        text = textwrap.dedent("""\
            Bobotie zonder pakje

            │ Description here

            source: https://example.com
            time: 45m
            servings: 4

            Ingredients:
              Crème fraîche            125 g
              Groene appel             1
              Kerriepoeder             8 tl
              Peper en zout

            Cookware:
              Ovenschaal
        """)
        ings = parse_ingredients(text)
        assert len(ings) == 3
        assert ings[0] == ("Crème fraîche", "125 g")
        assert ings[1] == ("Groene appel", "1")
        assert ings[2] == ("Kerriepoeder", "8 tl")

    def test_steps_not_mistaken_for_ingredients(self):
        text = textwrap.dedent("""\
            Ingredients:
              Ui                       1 stuks
            Steps:
              Snijd de Ui.
        """)
        ings = parse_ingredients(text)
        assert len(ings) == 1
        assert ings[0][0] == "Ui"


# ─── get_servings ─────────────────────────────────────────────────────────────


class TestGetServings:
    def test_simple_servings(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                title: Test Recipe
                servings: 4
                ---
                @Ingredient{1%stuks}
            """))
            path = f.name
        try:
            assert get_servings(path) == 4.0
        finally:
            os.unlink(path)

    def test_decimal_servings(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                title: Single Serve
                servings: 1
                ---
                @Ingredient{100%g}
            """))
            path = f.name
        try:
            assert get_servings(path) == 1.0
        finally:
            os.unlink(path)

    def test_no_servings_field(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                title: No Servings
                ---
                @Ingredient{1%stuks}
            """))
            path = f.name
        try:
            assert get_servings(path) is None
        finally:
            os.unlink(path)

    def test_non_numeric_servings(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                title: Range Servings
                servings: 4-6
                ---
                @Ingredient{1%stuks}
            """))
            path = f.name
        try:
            assert get_servings(path) is None
        finally:
            os.unlink(path)

    def test_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write("@Ingredient{1%stuks}\n")
            path = f.name
        try:
            assert get_servings(path) is None
        finally:
            os.unlink(path)

    def test_case_insensitive(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cook", delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                title: Test
                Servings: 2
                ---
                @Ingredient{1%stuks}
            """))
            path = f.name
        try:
            assert get_servings(path) == 2.0
        finally:
            os.unlink(path)