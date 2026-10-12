"""Smoke tests: package import, version and error hierarchy."""

import pytest

import calculator
from calculator.errors import CalculatorError, DivisionByZeroError, ParseError


def test_import_and_version():
    assert calculator.__version__ == "0.1.0"


def test_hierarchy():
    assert issubclass(CalculatorError, Exception)
    assert issubclass(ParseError, CalculatorError)
    assert issubclass(DivisionByZeroError, CalculatorError)


@pytest.mark.parametrize("cls", [CalculatorError, ParseError, DivisionByZeroError])
@pytest.mark.parametrize("builtin", [ZeroDivisionError, ValueError, ArithmeticError, SyntaxError])
def test_not_builtin_subclass(cls, builtin):
    assert not issubclass(cls, builtin)


def test_parse_error_with_position():
    e = ParseError("unexpected token", 3)
    assert str(e) == "unexpected token (at position 3)"
    assert e.message == "unexpected token"
    assert e.position == 3


def test_parse_error_position_zero():
    e = ParseError("empty expression", 0)
    assert str(e) == "empty expression (at position 0)"
    assert e.position == 0


def test_parse_error_without_position():
    e = ParseError("bad input")
    assert str(e) == "bad input"
    assert e.message == "bad input"
    assert e.position is None


def test_parse_error_is_raisable_and_catchable_as_base():
    with pytest.raises(CalculatorError) as info:
        raise ParseError("x", 1)
    assert info.value.position == 1


def test_division_by_zero_error():
    e = DivisionByZeroError()
    assert str(e) == "division by zero"
    assert e.message == "division by zero"
    with pytest.raises(CalculatorError, match="^division by zero$"):
        raise e
