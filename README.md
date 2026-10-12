# calculator

A small arithmetic expression calculator for Python 3.10+ that uses only the
standard library. You can use it as a library (`calculator.evaluate`) or from
the command line (`calc`, or `python -m calculator`).

Each expression goes through three steps:

1. A hand-written character scanner turns the text into tokens.
2. A recursive-descent parser checks the **whole** expression and produces a
   postfix (RPN) program.
3. An iterative stack machine runs that program.

The package does not use `eval`, `exec`, `compile`, `ast` or `re`.

---

## Install

```sh
python3 -m venv .venv && .venv/bin/python -m pip install '.[test]'
```

The `test` extra installs `pytest` and `pytest-cov`, which are only needed for
development. At runtime the package depends on nothing outside the standard
library. To get the `calc` command, either activate the virtual environment
(`. .venv/bin/activate`) or call it as `.venv/bin/calc`.

---

## Library usage

```python
>>> from calculator import evaluate
>>> evaluate('2 + 3 * (4 - 1)')
11
>>> evaluate('4 / 2')
2.0
>>> evaluate('0.1 + 0.2')
0.30000000000000004
```

`evaluate(expression: str) -> int | float`

- If an expression uses only integer literals and `+`, `-`, `*`, the result is
  an `int`.
- `/` is always true division, so it returns a `float` even when the division
  is exact (`evaluate('4 / 2') == 2.0`).
- A decimal literal such as `1.5` or `.5` is a `float`, and any arithmetic
  involving it gives a `float`.
- The library returns the raw Python value. The integer-style display of
  whole-number floats (see [Output formatting](#output-formatting)) only
  applies to the CLI.

The top-level package exports `evaluate`, `CalculatorError`, `ParseError`,
`DivisionByZeroError` and `__version__` (`'0.1.0'`).

---

## CLI usage

```sh
$ calc '2 + 3 * (4 - 1)'
11
$ python -m calculator '2 + 3 * (4 - 1)'
11
$ calc '4 / 2'
2
$ calc '7 / 2'
3.5
```

> **⚠️ Always quote the expression.**
> The shell treats some calculator characters specially. If you leave them
> unquoted, `*` is expanded to the file names in the current directory, and
> `(` / `)` are shell syntax (`calc (1 + 2)` is a shell error). Put the whole
> expression in single quotes: `calc '2 * (3 + 4)'`.

If you pass more than one argument, they are joined with single spaces and
treated as one expression. So `calc 2 + 3` is the same as `calc '2 + 3'`.
This only works safely for expressions without `*` or parentheses, so quoting
is still the recommended habit.

The CLI reads expressions from its arguments only (see [Non-goals](#non-goals)).

---

## Grammar

Here is the grammar in EBNF. It has four rules, from lowest to highest
precedence:

```ebnf
expression = term  , { ( "+" | "-" ) , term  } ;   (* left-associative *)
term       = unary , { ( "*" | "/" ) , unary } ;   (* left-associative *)
unary      = ( "+" | "-" ) , unary | primary ;
primary    = NUMBER | "(" , expression , ")" ;

NUMBER     = DIGITS , [ "." , DIGITS ]             (* 3, 3.25 *)
           | "." , DIGITS ;                        (* .5      *)
DIGITS     = digit , { digit } ;
```

Whitespace between tokens is ignored.

- **Operators:** binary `+ - * /` with the usual precedence. `*` and `/` bind
  tighter than `+` and `-`, and all four are left-associative
  (`8 - 3 - 2` = 3, `8 / 4 / 2` = 1.0).
- **Unary `+` and `-`** are accepted and can be repeated: `--3` = 3, `+3` = 3,
  `-+-3` = 3. Unary operators bind **tighter** than `*` and `/`, so `-2 * 3`
  means `(-2) * 3` and `2 * -3` is valid.
- **Literals:** integers (`42`) and decimals (`3.14`, `.5`).
- **Rejected** (each raises `ParseError`):
  - a trailing decimal point with no digits after it: `5.`
  - scientific notation: `1e3`, `2E-4`
  - implicit multiplication: `2(3)`, `(1)(2)`, `2 3`
  - any character that is not a digit, `.`, an operator, a parenthesis or
    whitespace

---

## Output formatting

The CLI formats results like this:

| Result value                                     | Printed as     | Example input → output             |
|--------------------------------------------------|----------------|------------------------------------|
| `int`                                            | `str(x)`       | `2 + 3` → `5`                      |
| finite whole-number `float` with `abs(x) < 2**53`| integer, no `.0` | `4 / 2` → `2`                    |
| any other `float`                                | `repr(x)`      | `7 / 2` → `3.5`, `0.1 + 0.2` → `0.30000000000000004` |

The 2\*\*53 limit is the range in which every integer can be represented
exactly as a float, so dropping the `.0` never changes the value. Whole-number
floats at or above 2**53 in magnitude, and non-finite floats, are printed with
`repr()` (for example `1e+16`).

This formatting is only for display. `evaluate('4 / 2')` still returns `2.0`.

---

## Errors

### Exception hierarchy

```
Exception
└── CalculatorError            base class for every calculator error
    ├── ParseError             lexical/syntax error; has .message and .position
    └── DivisionByZeroError    message is always 'division by zero'
```

- `CalculatorError` only subclasses `Exception`. Neither it nor its subclasses
  inherit from `ZeroDivisionError`, `ValueError`, `ArithmeticError` or
  `SyntaxError`. Catch `CalculatorError` (or a subclass) explicitly.
- `ParseError(message, position=None)` has two attributes:
  - `.message`: the bare description.
  - `.position`: the 0-based character offset in the input where the problem
    was found, or `None`.

  `str(err)` is `"<message> (at position <N>)"` when a position is set,
  otherwise just `"<message>"`.
- `DivisionByZeroError()` has `.message == str(err) == 'division by zero'`.

```python
>>> from calculator import evaluate, CalculatorError, ParseError, DivisionByZeroError
>>> try:
...     evaluate('1 / 0')
... except DivisionByZeroError as e:
...     print(e)
division by zero
>>> try:
...     evaluate('2 +')
... except ParseError as e:
...     print(e.position)
3
```

### Message catalogue

| Exception             | Raised when                                                                                     |
|-----------------------|-------------------------------------------------------------------------------------------------|
| `ParseError`          | the expression is empty or contains only whitespace                                             |
| `ParseError`          | the input contains a character that is not allowed (position = that character)                 |
| `ParseError`          | a number is malformed, e.g. `5.`, or it is followed directly by `e`/`E` (scientific notation)    |
| `ParseError`          | a token appears where it is not allowed, e.g. `2 3`, `2(3)`, `* 2`, `(1)(2)`                     |
| `ParseError`          | the expression ends too early, e.g. `2 +`, `-` (position = end of input)                        |
| `ParseError`          | a `(` is never closed, e.g. `(1 + 2`                                                            |
| `ParseError`          | there is a `)` with no matching `(`, e.g. `1 + 2)`                                              |
| `DivisionByZeroError` | the right-hand side of `/` evaluates to zero (`1 / 0`, `1 / (2 - 2)`, `1 / 0.0`). Message: `division by zero` |

`division by zero` is a fixed message and part of the public contract. The
exact text of each `ParseError` message is set by the tokenizer and parser.
The stable parts are the exception type, the `.position` attribute and the
`"<message> (at position <N>)"` format.

### Syntax errors come first

The parser checks the entire expression before any arithmetic happens. If an
expression has both a syntax error and a division by zero, you get the
`ParseError`:

```python
>>> evaluate('1 / 0 +')     # ParseError, not DivisionByZeroError
```

---

## Exit codes

| Exit code | Meaning                                                                                      |
|-----------|----------------------------------------------------------------------------------------------|
| `0`       | Success. The formatted result is printed to stdout.                                          |
| `1`       | A calculator error (any `CalculatorError`). `calc: error: <message>` is printed to stderr.   |
| `2`       | Usage error (no expression argument given). Usage text is printed.                           |

```sh
$ calc '1 / 0'
calc: error: division by zero
$ echo $?
1

$ calc '2 +'
calc: error: <parse error message> (at position 3)
$ echo $?
1

$ calc
usage: ...
$ echo $?
2
```

`<message>` is `str()` of the exception, so parse errors include their
position.

---

## Non-goals

- **No stdin input and no REPL/interactive mode.** Expressions are taken from
  command-line arguments only.
- No variables, functions, exponentiation, modulo, scientific-notation
  literals or implicit multiplication.
- No arbitrary-precision decimals. Arithmetic uses Python `int` and `float`.

---

## Running tests

Install with the `test` extra (see [Install](#install)), then run:

```sh
pytest
```

To run with coverage:

```sh
pytest --cov=calculator --cov-report=term-missing
```

Coverage measures branches and must reach **90%** or more. The threshold is set
as `fail_under = 90` under `[tool.coverage.report]` in `pyproject.toml`, so the
coverage run fails if total coverage drops below 90%. Plain `pytest` does not
measure coverage.

The test suite also includes a static check (`tests/test_no_eval.py`) that
fails if any module in `src/calculator` calls `eval`, `exec`, `compile` or
`__import__`.
