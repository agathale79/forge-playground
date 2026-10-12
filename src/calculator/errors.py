"""Exception hierarchy for the calculator package.

All errors raised by the calculator derive from :class:`CalculatorError`.
None of these classes subclass a built-in exception other than
:class:`Exception`, so callers must catch ``CalculatorError`` (or one of its
subclasses) explicitly.
"""

from __future__ import annotations

__all__ = ["CalculatorError", "ParseError", "DivisionByZeroError"]


class CalculatorError(Exception):
    """Base class for every error raised by the calculator."""


class ParseError(CalculatorError):
    """A lexical or syntax error in the input expression.

    :param message: human-readable description of the problem.
    :param position: 0-based character offset in the expression where the
        error was detected, or ``None`` if not applicable.
    """

    def __init__(self, message: str, position: int | None = None) -> None:
        self.message = message
        self.position = position
        super().__init__(message, position)

    def __str__(self) -> str:
        if self.position is not None:
            return f"{self.message} (at position {self.position})"
        return self.message


class DivisionByZeroError(CalculatorError):
    """Raised when the evaluator divides by zero."""

    def __init__(self) -> None:
        self.message = "division by zero"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
