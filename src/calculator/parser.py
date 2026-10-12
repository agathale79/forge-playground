"""Recursive-descent parser producing a postfix (RPN) program.

The parser consumes the token list produced by
:func:`calculator.tokenizer.tokenize`, validates the *whole* expression and
returns a flat tuple of instructions for the stack evaluator. Because the
entire input is checked before anything is returned, syntax errors are always
reported before any arithmetic runs.

Grammar (lowest to highest precedence)::

    expression := term (('+' | '-') term)*
    term       := unary (('*' | '/') unary)*
    unary      := ('+' | '-')* primary
    primary    := NUMBER | '(' expression ')'

Instructions are:

* ``int`` / ``float`` -- push the literal value;
* ``'+'``, ``'-'``, ``'*'``, ``'/'`` -- pop right then left operand, push the
  result of ``left <op> right``;
* ``'neg'`` -- pop one operand and push its negation.
"""

from __future__ import annotations

from typing import Sequence, Union

from calculator.errors import ParseError
from calculator.tokenizer import Token, TokenKind

__all__ = ["Instruction", "MAX_NESTING", "parse"]

Instruction = Union[int, float, str]

#: Maximum parenthesis nesting depth accepted by :func:`parse`.
MAX_NESTING = 100

_ADDITIVE: dict[TokenKind, str] = {TokenKind.PLUS: "+", TokenKind.MINUS: "-"}
_MULTIPLICATIVE: dict[TokenKind, str] = {TokenKind.STAR: "*", TokenKind.SLASH: "/"}


def _describe(token: Token) -> str:
    """Return a short human-readable description of *token* for messages."""
    if token.kind is TokenKind.EOF:
        return "end of expression"
    return f"'{token.text}'"


class _Parser:
    """Single-use parser state over a token sequence."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = tokens
        self._index = 0
        self._depth = 0
        self._output: list[Instruction] = []

    # -- token helpers -------------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._index]

    def _advance(self) -> Token:
        # Callers only advance after peeking a non-EOF token, so the index
        # never moves past the terminating EOF.
        token = self._tokens[self._index]
        self._index += 1
        return token

    # -- grammar rules -------------------------------------------------

    def parse(self) -> tuple[Instruction, ...]:
        if self._peek().kind is TokenKind.EOF:
            raise ParseError("empty expression", self._peek().position)

        self._expression()

        leftover = self._peek()
        if leftover.kind is not TokenKind.EOF:
            raise self._unexpected(leftover)
        return tuple(self._output)

    def _expression(self) -> None:
        self._term()
        while self._peek().kind in _ADDITIVE:
            op = _ADDITIVE[self._advance().kind]
            self._term()
            self._output.append(op)

    def _term(self) -> None:
        self._unary()
        while self._peek().kind in _MULTIPLICATIVE:
            op = _MULTIPLICATIVE[self._advance().kind]
            self._unary()
            self._output.append(op)

    def _unary(self) -> None:
        minus_count = 0
        while self._peek().kind in _ADDITIVE:
            if self._advance().kind is TokenKind.MINUS:
                minus_count += 1
        self._primary()
        if minus_count % 2 == 1:
            self._output.append("neg")

    def _primary(self) -> None:
        token = self._peek()

        if token.kind is TokenKind.NUMBER:
            self._advance()
            assert token.value is not None
            self._output.append(token.value)
            return

        if token.kind is TokenKind.LPAREN:
            self._advance()
            self._depth += 1
            if self._depth > MAX_NESTING:
                raise ParseError(
                    f"expression nested too deeply (limit {MAX_NESTING})",
                    token.position,
                )
            self._expression()
            closing = self._peek()
            if closing.kind is TokenKind.RPAREN:
                self._advance()
                self._depth -= 1
                return
            if closing.kind is TokenKind.EOF:
                raise ParseError("missing ')' to close '('", token.position)
            # Something other than ')' follows a complete inner expression,
            # e.g. '(1 2)' or '(2(3))'.
            raise self._unexpected(closing)

        raise ParseError(
            f"expected a number or '(' but found {_describe(token)}",
            token.position,
        )

    # -- errors --------------------------------------------------------

    @staticmethod
    def _unexpected(token: Token) -> ParseError:
        """Build the error for a token that cannot follow a complete expression."""
        if token.kind is TokenKind.RPAREN:
            return ParseError("unexpected ')'", token.position)
        if token.kind is TokenKind.NUMBER:
            return ParseError(f"unexpected number '{token.text}'", token.position)
        return ParseError(f"unexpected {_describe(token)}", token.position)


def parse(tokens: Sequence[Token]) -> tuple[Instruction, ...]:
    """Parse *tokens* into a postfix (RPN) instruction tuple.

    :param tokens: tokens as returned by :func:`calculator.tokenizer.tokenize`;
        the sequence must be terminated by an ``EOF`` token.
    :returns: the RPN program, e.g. ``(1, 2, 3, '*', '+')`` for ``1 + 2 * 3``.
    :raises ParseError: if the expression is empty, malformed, has unbalanced
        parentheses, or is nested deeper than :data:`MAX_NESTING`.
    """
    if not tokens or tokens[-1].kind is not TokenKind.EOF:
        end = tokens[-1].position + len(tokens[-1].text) if tokens else 0
        tokens = [*tokens, Token(TokenKind.EOF, "", end)]
    return _Parser(tokens).parse()
