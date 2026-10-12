"""Iterative stack evaluator for postfix (RPN) programs.

:func:`run` executes a program produced by :func:`calculator.parser.parse`
using an explicit list as the operand stack; it never recurses, so very long
expressions cannot exhaust the Python call stack.

:func:`evaluate` is the public entry point: it tokenizes, parses (validating
the whole expression) and only then runs the program, so syntax errors are
always reported before any arithmetic error such as division by zero.
"""

from __future__ import annotations

from typing import Iterable, Union

from calculator.errors import CalculatorError, DivisionByZeroError
from calculator.parser import Instruction, parse
from calculator.tokenizer import tokenize

__all__ = ["run", "evaluate"]

Number = Union[int, float]

_OVERFLOW_MESSAGE = "numeric overflow: result too large to represent"
_BINARY_OPS = frozenset({"+", "-", "*", "/"})


def _invalid_program(detail: str) -> CalculatorError:
    return CalculatorError(f"invalid program: {detail}")


def run(program: Iterable[Instruction]) -> Number:
    """Execute an RPN *program* and return the single resulting value.

    :param program: instructions as produced by :func:`calculator.parser.parse`.
    :raises DivisionByZeroError: if a ``'/'`` has a zero right operand
        (``0``, ``0.0`` or ``-0.0``).
    :raises CalculatorError: on numeric overflow, or if the program is
        malformed (stack underflow, unknown instruction, leftover values).
    """
    stack: list[Number] = []
    push = stack.append
    pop = stack.pop

    try:
        for instruction in program:
            if isinstance(instruction, str):
                if instruction in _BINARY_OPS:
                    if len(stack) < 2:
                        raise _invalid_program("stack underflow")
                    right = pop()
                    left = pop()
                    if instruction == "+":
                        push(left + right)
                    elif instruction == "-":
                        push(left - right)
                    elif instruction == "*":
                        push(left * right)
                    else:
                        if right == 0:
                            raise DivisionByZeroError()
                        push(left / right)
                elif instruction == "neg":
                    if not stack:
                        raise _invalid_program("stack underflow")
                    push(-pop())
                else:
                    raise _invalid_program(f"unknown instruction {instruction!r}")
            else:
                push(instruction)
    except OverflowError:
        raise CalculatorError(_OVERFLOW_MESSAGE) from None

    if len(stack) != 1:
        raise _invalid_program(f"expected 1 result, found {len(stack)}")
    return stack[0]


def evaluate(expression: str) -> Number:
    """Evaluate an arithmetic *expression* and return its value.

    Integer-only expressions without ``/`` yield an ``int``; any decimal
    literal or division yields a ``float``.

    :raises TypeError: if *expression* is not a ``str``.
    :raises ParseError: if the expression is lexically or syntactically
        invalid (always reported before any evaluation error).
    :raises DivisionByZeroError: on division by zero.
    :raises CalculatorError: on numeric overflow.
    """
    if not isinstance(expression, str):
        raise TypeError(
            f"expression must be a str, not {type(expression).__name__}"
        )
    return run(parse(tokenize(expression)))
