"""Command-line interface for the calculator (``calc`` / ``python -m calculator``).

Arguments are joined with single spaces and evaluated as one expression, so
both ``calc '2 + 3'`` and ``calc 2 + 3`` work.  Quoting is recommended because
the shell may otherwise interpret characters such as ``*`` and ``(``.

Exit codes:

* ``0`` -- success; the formatted result is printed to stdout.
* ``1`` -- any :class:`~calculator.errors.CalculatorError`; the message is
  printed to stderr as ``calc: error: <message>``.
* ``2`` -- usage error (no expression given); usage text goes to stderr.

Argument handling is deliberately hand-written (no option parser) so that
expressions starting with ``-`` such as ``-3 + 5`` are not mistaken for
options.
"""

from __future__ import annotations

import math
import sys
from typing import Sequence, Union

from calculator.errors import CalculatorError
from calculator.evaluator import evaluate

__all__ = ["main", "format_result", "USAGE"]

USAGE = (
    "usage: calc '<expression>'  "
    "(quote the expression; exit codes: 0 ok, 1 calculator error, 2 usage)"
)

_EXACT_FLOAT_LIMIT = 2**53
_HELP_FLAGS = (["-h"], ["--help"])


def format_result(value: Union[int, float]) -> str:
    """Format an evaluation result for display.

    * ``int`` values are shown with :func:`str`.
    * Finite, integral floats with ``abs(x) < 2**53`` are shown as integers
      (``2.0`` -> ``'2'``, ``-0.0`` -> ``'0'``).
    * Every other float is shown with :func:`repr` (``3.5``, ``1e+20``,
      ``inf``, ``9007199254740992.0``).

    :raises CalculatorError: if the integer is too large to convert to text
        under the interpreter's int max-str-digits limit.
    """
    try:
        if isinstance(value, float):
            if (
                math.isfinite(value)
                and value.is_integer()
                and abs(value) < _EXACT_FLOAT_LIMIT
            ):
                return str(int(value))
            return repr(value)
        return str(value)
    except ValueError:
        raise CalculatorError("result too large to display") from None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code.

    :param argv: command-line arguments excluding the program name; defaults
        to ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]
    args = list(argv)

    if not args:
        print(USAGE, file=sys.stderr)
        return 2
    if args in _HELP_FLAGS:
        print(USAGE)
        return 0

    expression = " ".join(args)
    try:
        print(format_result(evaluate(expression)))
    except CalculatorError as exc:
        print(f"calc: error: {exc}", file=sys.stderr)
        return 1
    return 0
