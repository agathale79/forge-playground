"""Tests for calculator.parser: RPN shape, error reporting and nesting limit."""

import pytest

from calculator.errors import ParseError
from calculator.parser import MAX_NESTING, parse
from calculator.tokenizer import Token, TokenKind, tokenize


def p(expression):
    return parse(tokenize(expression))


def parse_error(expression):
    with pytest.raises(ParseError) as info:
        p(expression)
    return info.value


# --------------------------------------------------------------------------
# RPN shape
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("1 + 2 * 3", (1, 2, 3, "*", "+")),
        ("8 - 3 - 2", (8, 3, "-", 2, "-")),
        ("8 / 4 / 2", (8, 4, "/", 2, "/")),
        ("(1 + 2) * 3", (1, 2, "+", 3, "*")),
        ("--3", (3,)),
        ("-3", (3, "neg")),
        ("+3", (3,)),
        ("2 * -(1 + 1)", (2, 1, 1, "+", "neg", "*")),
        ("-+-3", (3,)),
        ("---3", (3, "neg")),
        ("-2 * 3", (2, "neg", 3, "*")),
        ("1 - 2 + 3", (1, 2, "-", 3, "+")),
        ("2 * 3 + 4 / 5", (2, 3, "*", 4, 5, "/", "+")),
        ("42", (42,)),
        ("((7))", (7,)),
    ],
)
def test_rpn_shape(expression, expected):
    assert p(expression) == expected


def test_result_is_tuple():
    assert isinstance(p("1 + 2"), tuple)


def test_number_types_preserved():
    program = p("1 + 2.5 + .5")
    assert program == (1, 2.5, "+", 0.5, "+")
    assert type(program[0]) is int
    assert type(program[1]) is float
    assert type(program[3]) is float


# --------------------------------------------------------------------------
# Malformed input: one test per category
# --------------------------------------------------------------------------


@pytest.mark.parametrize("expression, position", [("", 0), ("   ", 3)])
def test_empty_expression(expression, position):
    err = parse_error(expression)
    assert err.message == "empty expression"
    assert err.position == position


def test_trailing_operator():
    err = parse_error("2 +")
    assert err.message == "expected a number or '(' but found end of expression"
    assert err.position == 3


def test_leading_binary_operator():
    err = parse_error("* 2")
    assert err.message == "expected a number or '(' but found '*'"
    assert err.position == 0


def test_consecutive_binary_operators():
    err = parse_error("1 + * 2")
    assert err.message == "expected a number or '(' but found '*'"
    assert err.position == 4


def test_unclosed_paren():
    err = parse_error("(1 + 2")
    assert "missing ')'" in err.message
    assert err.message == "missing ')' to close '('"
    assert err.position == 0


def test_unclosed_inner_paren_reports_innermost_open():
    err = parse_error("(1 + (2")
    assert err.message == "missing ')' to close '('"
    assert err.position == 5


def test_unmatched_close_paren():
    err = parse_error("1 + 2)")
    assert err.message == "unexpected ')'"
    assert err.position == 5


def test_empty_parens():
    err = parse_error("()")
    assert err.message == "expected a number or '(' but found ')'"
    assert err.position == 1


def test_adjacent_numbers():
    err = parse_error("2 3")
    assert err.message == "unexpected number '3'"
    assert err.position == 2


def test_implicit_multiplication():
    err = parse_error("2(3)")
    assert err.message == "unexpected '('"
    assert err.position == 1


def test_adjacent_tokens_inside_parens():
    err = parse_error("(1 2)")
    assert err.message == "unexpected number '2'"
    assert err.position == 3


def test_lone_unary_minus():
    err = parse_error("-")
    assert err.message == "expected a number or '(' but found end of expression"
    assert err.position == 1


def test_str_includes_position():
    assert str(parse_error("2 +")) == (
        "expected a number or '(' but found end of expression (at position 3)"
    )


def test_syntax_error_reported_even_after_division_by_zero():
    # Parsing never evaluates, so '1 / 0 +' is a ParseError.
    err = parse_error("1 / 0 +")
    assert err.position == 7


# --------------------------------------------------------------------------
# Nesting limit
# --------------------------------------------------------------------------


def test_max_nesting_constant():
    assert MAX_NESTING == 100


def test_max_nesting_allowed():
    expression = "(" * 100 + "1" + ")" * 100
    assert p(expression) == (1,)


def test_max_nesting_with_unary_and_operators():
    expression = "-(" * 100 + "1 + 2" + ")" * 100
    assert p(expression) == (1, 2, "+") + ("neg",) * 100


def test_nesting_too_deep():
    expression = "(" * 101 + "1" + ")" * 101
    err = parse_error(expression)
    assert err.message == "expression nested too deeply (limit 100)"
    assert "nested too deeply" in str(err)
    assert err.position == 100


def test_sequential_groups_do_not_accumulate_depth():
    group = "(" * 100 + "1" + ")" * 100
    assert p(group + " + " + group) == (1, 1, "+")


def test_very_deep_nesting_raises_parse_error_not_recursion_error():
    err = parse_error("(" * 10_000 + "1" + ")" * 10_000)
    assert "nested too deeply" in err.message


# --------------------------------------------------------------------------
# Token sequences without a terminating EOF
# --------------------------------------------------------------------------


def test_empty_token_sequence():
    with pytest.raises(ParseError) as info:
        parse([])
    assert info.value.message == "empty expression"
    assert info.value.position == 0


def test_missing_eof_is_tolerated():
    tokens = [t for t in tokenize("12 + 3") if t.kind is not TokenKind.EOF]
    assert parse(tokens) == (12, 3, "+")


def test_missing_eof_error_position_is_end_of_input():
    tokens = [Token(TokenKind.NUMBER, "12", 0, 12), Token(TokenKind.PLUS, "+", 3)]
    with pytest.raises(ParseError) as info:
        parse(tokens)
    assert info.value.position == 4
