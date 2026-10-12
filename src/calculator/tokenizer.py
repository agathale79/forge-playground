"""Hand-written character scanner for calculator expressions.

The scanner turns an expression string into a list of :class:`Token` objects
terminated by an ``EOF`` token. It does not use the ``re`` module.

Grammar of number literals (DIGITS are ASCII ``0``-``9`` only)::

    NUMBER := DIGITS ('.' DIGITS)? | '.' DIGITS

Integer literals carry an ``int`` value; decimal literals carry a ``float``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from calculator.errors import ParseError

__all__ = ["TokenKind", "Token", "tokenize"]


class TokenKind(Enum):
    """The kinds of token produced by :func:`tokenize`."""

    NUMBER = "NUMBER"
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """A single lexical token.

    :param kind: the token kind.
    :param text: the exact source text of the token ('' for EOF).
    :param position: 0-based offset of the token's first character.
    :param value: numeric value for NUMBER tokens, otherwise ``None``.
    """

    kind: TokenKind
    text: str
    position: int
    value: int | float | None = None


_SINGLE_CHAR_TOKENS: dict[str, TokenKind] = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
}


def _is_digit(ch: str) -> bool:
    """Return True only for the ASCII digits 0-9."""
    return "0" <= ch <= "9"


def _scan_digits(expression: str, index: int) -> int:
    """Return the index just past a run of ASCII digits starting at *index*."""
    length = len(expression)
    while index < length and _is_digit(expression[index]):
        index += 1
    return index


def _scan_number(expression: str, start: int) -> tuple[Token, int]:
    """Scan a number literal starting at *start*.

    Returns the NUMBER token and the index just past it.
    """
    length = len(expression)
    index = _scan_digits(expression, start)
    is_decimal = False

    if index < length and expression[index] == ".":
        is_decimal = True
        frac_start = index + 1
        index = _scan_digits(expression, frac_start)
        if index == frac_start:
            # '5.' or a lone '.': a decimal point must be followed by digits.
            text = expression[start:frac_start]
            raise ParseError(f"invalid number '{text}'", start)

    text = expression[start:index]
    value: int | float
    if is_decimal:
        value = float(text)
    else:
        try:
            value = int(text)
        except ValueError:
            # Exceeds sys.get_int_max_str_digits() (Python 3.11+ / patched 3.10).
            raise ParseError("number too long", start) from None
    return Token(TokenKind.NUMBER, text, start, value), index


def tokenize(expression: str) -> list[Token]:
    """Scan *expression* into tokens.

    The returned list always ends with an ``EOF`` token whose position is
    ``len(expression)`` and whose text is ``''``.

    :raises ParseError: on an unexpected character, a malformed number
        literal, or an integer literal too long to convert.
    """
    tokens: list[Token] = []
    index = 0
    length = len(expression)

    while index < length:
        ch = expression[index]

        if ch.isspace():
            index += 1
            continue

        kind = _SINGLE_CHAR_TOKENS.get(ch)
        if kind is not None:
            tokens.append(Token(kind, ch, index))
            index += 1
            continue

        if _is_digit(ch) or ch == ".":
            token, index = _scan_number(expression, index)
            tokens.append(token)
            continue

        raise ParseError(f"unexpected character '{ch}'", index)

    tokens.append(Token(TokenKind.EOF, "", length))
    return tokens
