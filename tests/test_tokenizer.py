"""Tests for the hand-written tokenizer."""

import sys

import pytest

from calculator.errors import CalculatorError, ParseError
from calculator.tokenizer import Token, TokenKind, tokenize

K = TokenKind


def _triples(expression):
    return [(t.kind, t.text, t.position) for t in tokenize(expression)]


def test_kinds_texts_positions():
    assert _triples("2 + 3*(4-1)") == [
        (K.NUMBER, "2", 0),
        (K.PLUS, "+", 2),
        (K.NUMBER, "3", 4),
        (K.STAR, "*", 5),
        (K.LPAREN, "(", 6),
        (K.NUMBER, "4", 7),
        (K.MINUS, "-", 8),
        (K.NUMBER, "1", 9),
        (K.RPAREN, ")", 10),
        (K.EOF, "", 11),
    ]


def test_all_operator_kinds():
    assert [t.kind for t in tokenize("+-*/()")] == [
        K.PLUS, K.MINUS, K.STAR, K.SLASH, K.LPAREN, K.RPAREN, K.EOF,
    ]


def test_operator_tokens_have_no_value():
    for tok in tokenize("+-*/()"):
        assert tok.value is None


@pytest.mark.parametrize(
    "text, expected, typ",
    [
        ("3", 3, int),
        ("2.5", 2.5, float),
        (".5", 0.5, float),
        ("0", 0, int),
        ("007", 7, int),
        ("10.0", 10.0, float),
        ("123.456", 123.456, float),
    ],
)
def test_number_values(text, expected, typ):
    tokens = tokenize(text)
    assert len(tokens) == 2
    num = tokens[0]
    assert num.kind is K.NUMBER
    assert num.text == text
    assert num.position == 0
    assert num.value == expected
    assert type(num.value) is typ


def test_whitespace_spaces_tabs_newlines():
    tokens = tokenize(" \t1\n+\t 2 \n")
    assert [(t.kind, t.position) for t in tokens] == [
        (K.NUMBER, 2),
        (K.PLUS, 4),
        (K.NUMBER, 7),
        (K.EOF, 10),
    ]


def test_whitespace_only():
    assert tokenize(" \t\n ") == [Token(K.EOF, "", 4)]


@pytest.mark.parametrize("expr", ["1", "2 + .5", "  ", "(1)  "])
def test_eof_position_is_length(expr):
    eof = tokenize(expr)[-1]
    assert eof.kind is K.EOF
    assert eof.text == ""
    assert eof.position == len(expr)
    assert eof.value is None


def test_example_from_spec():
    t = tokenize("2 + .5")
    assert [x.kind for x in t] == [K.NUMBER, K.PLUS, K.NUMBER, K.EOF]
    assert t[0].value == 2 and isinstance(t[0].value, int)
    assert t[2].value == 0.5
    assert t[3].position == 6


def test_empty_string_returns_only_eof():
    assert tokenize("") == [Token(K.EOF, "", 0)]


def test_tokens_are_frozen():
    tok = tokenize("1")[0]
    with pytest.raises(Exception):
        tok.position = 5  # type: ignore[misc]


def test_adjacent_numbers_are_separate_tokens():
    # '1.2.3' scans as '1.2' then '.3'; the parser rejects the sequence.
    tokens = tokenize("1.2.3")
    assert [(t.text, t.position) for t in tokens[:-1]] == [("1.2", 0), (".3", 3)]


@pytest.mark.parametrize(
    "expr, fragment, position",
    [
        ("2 $ 3", "unexpected character '$'", 2),
        ("5.", "invalid number '5.'", 0),
        (".", "invalid number '.'", 0),
        ("1 + 5. * 2", "invalid number '5.'", 4),
        ("3 + .", "invalid number '.'", 4),
        ("5.x", "invalid number '5.'", 0),
        ("1e3", "unexpected character 'e'", 1),
        ("1,5", "unexpected character ','", 1),
        ("x", "unexpected character 'x'", 0),
        ("2 ** 3 %", "unexpected character '%'", 7),
    ],
)
def test_parse_errors(expr, fragment, position):
    with pytest.raises(ParseError) as excinfo:
        tokenize(expr)
    err = excinfo.value
    assert fragment in err.message
    assert fragment in str(err)
    assert err.position == position
    assert isinstance(err, CalculatorError)


def test_non_ascii_digit_rejected():
    # Arabic-Indic digit three: str.isdigit() is True but it is not ASCII.
    with pytest.raises(ParseError) as excinfo:
        tokenize("1 + \u0663")
    assert "unexpected character" in excinfo.value.message
    assert excinfo.value.position == 4


def test_superscript_digit_rejected():
    with pytest.raises(ParseError) as excinfo:
        tokenize("2\u00b2")
    assert excinfo.value.position == 1


@pytest.mark.skipif(
    not hasattr(sys, "get_int_max_str_digits"),
    reason="int max str digits limit not available",
)
def test_number_too_long():
    limit = sys.get_int_max_str_digits()
    if limit == 0:
        pytest.skip("int max str digits limit disabled")
    digits = "1" * (limit + 1)
    with pytest.raises(ParseError) as excinfo:
        tokenize("1 + " + digits)
    assert "number too long" in excinfo.value.message
    assert excinfo.value.position == 4


def test_long_decimal_is_fine():
    # float() has no digit limit, so long decimals still tokenize.
    tok = tokenize("1." + "0" * 10000)[0]
    assert tok.value == 1.0
    assert type(tok.value) is float
