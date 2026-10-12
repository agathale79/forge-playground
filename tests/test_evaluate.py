"""Tests for the iterative evaluator and the public evaluate() API."""

import pytest

import calculator
from calculator import CalculatorError, DivisionByZeroError, ParseError, evaluate
from calculator.evaluator import run


# -- operators, precedence, associativity ---------------------------------


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("2 + 3", 5),
        ("5 - 8", -3),
        ("4 * 2.5", 10),
        ("7 / 2", 3.5),
        ("2 + 3 * 4", 14),
        ("10 - 6 / 2", 7),
        ("8 - 3 - 2", 3),
        ("8 / 4 / 2", 1),
        ("2 * 3 / 4", 1.5),
        ("(2 + 3) * 4", 20),
        ("((2 + 3) * (4 - (1 + 1)))", 10),
    ],
)
def test_operators_precedence_associativity(expr, expected):
    assert evaluate(expr) == expected


def test_mixed_expression_is_int():
    result = evaluate("2 + 3 * (4 - 1)")
    assert result == 11
    assert isinstance(result, int)


# -- unary, decimals, whitespace -------------------------------------------


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("-3 + 5", 2),
        ("2 * -(1 + 1)", -4),
        ("2 - -3", 5),
        ("--3", 3),
        ("+3", 3),
        ("-(-(2))", 2),
        ("-0", 0),
    ],
)
def test_unary(expr, expected):
    assert evaluate(expr) == expected


def test_decimals():
    assert evaluate(".5 + .5") == 1.0
    assert evaluate("0.1 + 0.2") == pytest.approx(0.3)
    assert evaluate("1.25 * 4") == pytest.approx(5.0)


@pytest.mark.parametrize(
    "expr",
    ["2+3*4", "  2 + 3 * 4  ", "\t2\t+\t3\t*\t4\t", "2\n+\n3\n*\n4", " 2+ 3 *4\r\n"],
)
def test_whitespace_variants(expr):
    assert evaluate(expr) == 14


# -- result types and long chains ------------------------------------------


def test_int_result_type():
    result = evaluate("2 + 3")
    assert result == 5
    assert isinstance(result, int)


def test_division_returns_float():
    result = evaluate("4 / 2")
    assert result == 2.0
    assert isinstance(result, float)


def test_decimal_literal_returns_float():
    assert isinstance(evaluate("1.0 + 1"), float)


def test_long_chain_does_not_recurse():
    assert evaluate("1" + " + 1" * 5000) == 5001


def test_long_unary_and_mixed_chain():
    assert evaluate("-" * 5001 + "1") == -1
    assert evaluate("2" + " * 1" * 3000 + " - 1" * 3000) == -2998


# -- errors -----------------------------------------------------------------


@pytest.mark.parametrize("expr", ["1 / 0", "5 / (2 - 2)", "1 / 0.0", "0 / 0", "1 / -0.0"])
def test_division_by_zero(expr):
    with pytest.raises(DivisionByZeroError) as info:
        evaluate(expr)
    assert "division by zero" in str(info.value)
    assert isinstance(info.value, CalculatorError)


def test_syntax_error_wins_over_division_by_zero():
    with pytest.raises(ParseError):
        evaluate("1 / 0 +")


def test_overflow_is_calculator_error():
    with pytest.raises(CalculatorError) as info:
        evaluate("9" * 400 + " / 3")
    err = info.value
    assert not isinstance(err, (ParseError, DivisionByZeroError))
    assert "overflow" in str(err)
    assert str(err) == "numeric overflow: result too large to represent"


def test_overflow_mixed_int_float():
    with pytest.raises(CalculatorError, match="overflow"):
        evaluate("9" * 400 + " + 0.5")


def test_huge_ints_without_division_are_exact():
    assert evaluate("9" * 400 + " - " + "9" * 400) == 0


@pytest.mark.parametrize("value", [None, 42, b"1 + 2", ["1"]])
def test_non_str_raises_type_error(value):
    with pytest.raises(TypeError):
        evaluate(value)


@pytest.mark.parametrize("expr", ["", "   ", "2 +", "(1 + 2", "1 + 2)", "2 $ 3", "2 3", "()"])
def test_malformed_inputs_raise_parse_error(expr):
    with pytest.raises(ParseError):
        evaluate(expr)


# -- run() on hand-built programs ------------------------------------------


def test_run_basic_programs():
    assert run((1, 2, 3, "*", "+")) == 7
    assert run((8, 3, "-", 2, "-")) == 3
    assert run((5, "neg")) == -5
    assert run((7, 2, "/")) == 3.5


def test_run_division_by_zero():
    with pytest.raises(DivisionByZeroError):
        run((1, 0, "/"))


@pytest.mark.parametrize(
    "program",
    [(), ("+",), (1, "+"), ("neg",), (1, 2), (1, "pow")],
)
def test_run_rejects_malformed_programs(program):
    with pytest.raises(CalculatorError, match="invalid program"):
        run(program)


# -- package surface ---------------------------------------------------------


def test_package_exports():
    assert set(calculator.__all__) == {
        "evaluate",
        "CalculatorError",
        "ParseError",
        "DivisionByZeroError",
        "__version__",
    }
    assert calculator.__version__ == "0.1.0"
    for name in calculator.__all__:
        assert hasattr(calculator, name)
