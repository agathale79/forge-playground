# Demo: `calculator`, a safe arithmetic expression calculator

## What it does

`calculator` is a small Python package with no dependencies outside the standard library. It evaluates arithmetic
expressions made of `+ - * /`, parentheses (nested is fine), unary minus, integers and
decimals. It has its own tokenizer, parser and evaluator, and never calls
`eval`, `exec` or `compile`. You can use it two ways:

- **Library:** `from calculator import evaluate; evaluate('2 + 3 * (4 - 1)')` returns `11`.
  When something goes wrong it raises its own documented exceptions:
  `CalculatorError`, which has two subclasses, `ParseError` and `DivisionByZeroError`.
- **CLI:** `calc '<expression>'` prints the result on stdout. Exit codes are
  `0` for success, `1` for a calculator error (message on stderr), and `2` for a usage error
  (no arguments).

## How to try it

The app is already installed in `/workspace/.venv`, using the run-spec command:

```sh
cd /workspace
python3 -m venv .venv && .venv/bin/python -m pip install '.[test]'
```

Run these from `/workspace`. If `/workspace/.venv/bin` is first on your `PATH`, you can type plain `calc`
instead of `.venv/bin/calc`.

```sh
.venv/bin/calc '2 + 3 * (4 - 1)'          # 11
.venv/bin/calc '8 - 3 - 2'                # 3   (left-associative)
.venv/bin/calc '8 / 4 / 2'                # 1   (a whole-number float prints without .0)
.venv/bin/calc '7 / 2'                    # 3.5
.venv/bin/calc '2 * -(1 + 1)'             # -4
.venv/bin/calc '-3 + 5'                   # 2   (a leading minus is not read as an option)
.venv/bin/calc '0.1 + 0.2'                # 0.30000000000000004
.venv/bin/calc 2 + 3                      # 5   (multiple args are joined; quote anything with * or parentheses)
.venv/bin/calc '1 / 0'; echo "exit=$?"    # stderr: calc: error: division by zero ; exit=1
.venv/bin/calc '(1 + 2'; echo "exit=$?"   # stderr: calc: error: missing ')' to close '(' (at position 0) ; exit=1
.venv/bin/calc '2 $ 3'; echo "exit=$?"    # stderr: calc: error: unexpected character '$' (at position 2) ; exit=1
.venv/bin/calc; echo "exit=$?"            # usage on stderr ; exit=2
.venv/bin/python -m calculator '((2 + 3) * (4 - (1 + 1)))'   # 10

.venv/bin/python -c "from calculator import evaluate; print(evaluate('2 + 3 * (4 - 1)'), evaluate('4 / 2'))"   # 11 2.0
.venv/bin/python -c "from calculator import evaluate; evaluate('5 / (2 - 2)')"
#   -> traceback ending in: calculator.errors.DivisionByZeroError: division by zero

# Test suite with coverage. /workspace is read-only in the preview, so the coverage data file goes to /tmp:
cd /workspace && COVERAGE_FILE=/tmp/.coverage .venv/bin/python -m pytest -p no:cacheprovider --cov=calculator --cov-report=term-missing
```

**Shell quoting:** always wrap the expression in single quotes. Without them, the shell
treats `*` as a filename wildcard, `(` `)` as syntax, and `$` as the start of a variable.

## Scenarios and results

I ran everything from a fresh shell (`env -i`, minimal PATH) against the installed
`/workspace/.venv`. The installed package is identical to `src/calculator`.

| # | Metric / story | Command | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | Library returns 11 | `.venv/bin/python -c "from calculator import evaluate; print(evaluate('2 + 3 * (4 - 1)'), evaluate('4 / 2'))"` | `11 2.0` | `11 2.0` | PASS |
| 2 | CLI prints 11, exit 0 | `.venv/bin/calc '2 + 3 * (4 - 1)'` | `11`, exit 0 | `11`, exit 0 | PASS |
| 3 | Precedence and left-associativity | `calc '8 - 3 - 2'`, `calc '8 / 4 / 2'`, `calc '7 / 2'` | `3`, `1`, `3.5` | `3`, `1`, `3.5` (library returns `3`, `1.0`) | PASS |
| 4 | Nested parentheses | `.venv/bin/python -m calculator '((2 + 3) * (4 - (1 + 1)))'` | `10` | `10` | PASS |
| 5 | Unary minus, decimals, whitespace, joined args | `calc '2 * -(1 + 1)'`, `calc '-3 + 5'`, `calc '0.1 + 0.2'`, `calc 2 + 3`, `evaluate('  1   +2 ')` | `-4`, `2`, `0.30000000000000004`, `5`, `3` | same | PASS |
| 6 | Division by zero, library | `evaluate('1 / 0')`, `evaluate('5 / (2 - 2)')` | `DivisionByZeroError` (a subclass of `CalculatorError`) | `DivisionByZeroError: division by zero` for both. The traceback has no chained `ZeroDivisionError` | PASS |
| 7 | Division by zero, CLI | `calc '1 / 0'`, `calc '5 / (2 - 2)'` | stderr contains "division by zero", exit ≠ 0 | `calc: error: division by zero` on stderr (stdout empty), exit 1 | PASS |
| 8 | Malformed input, library | `evaluate(x)` for `''`, `'2 +'`, `'(1 + 2'`, `'1 + 2)'`, `'2 $ 3'` (also `'   '`, `'1 2'`, `'()'`, `'2 ** 3'`) | `ParseError` with a clear message | `ParseError` every time, for example `empty expression (at position 0)`, `expected a number or '(' but found end of expression (at position 3)`, `missing ')' to close '(' (at position 0)`, `unexpected ')' (at position 5)`, `unexpected character '$' (at position 2)` | PASS |
| 9 | Malformed input, CLI | `calc ''`, `calc '2 +'`, `calc '(1 + 2'`, `calc '1 + 2)'`, `calc '2 $ 3'` | one-line message on stderr, exit ≠ 0, no traceback | `calc: error: …` messages as above, exit 1, no traceback | PASS |
| 10 | CLI usage error | `.venv/bin/calc; echo "exit=$?"` | usage on stderr, exit 2 | `usage: calc '<expression>' …` on stderr, exit 2 | PASS |
| 11 | Every pytest test passes on a clean checkout | `git clone /workspace /tmp/cc && cd /tmp/cc && /workspace/.venv/bin/pytest -q -p no:cacheprovider` | all pass | `213 passed` | PASS |
| 12 | Coverage ≥ 90% | `COVERAGE_FILE=/tmp/.coverage .venv/bin/python -m pytest -p no:cacheprovider --cov=calculator --cov-report=term-missing` | all pass, ≥ 90% | `213 passed`, 100% line and branch coverage | PASS |
| 13 | A test exists for each in-scope behaviour | Read the test names in `tests/` | One test per operator, precedence, associativity, nesting, unary, decimals, whitespace, div-by-zero, each malformed category, CLI success and CLI error exit | All present (for example `test_operators_precedence_associativity`, `test_unary`, `test_decimals`, `test_whitespace_variants`, `test_division_by_zero`, `test_empty_expression`, `test_trailing_operator`, `test_unclosed_paren`, `test_unmatched_close_paren`, `test_main_unexpected_character_message`, `test_subprocess_success`, `test_subprocess_calculator_errors`) | PASS |
| 14 | No eval/exec/compile | `grep -nE '\b(eval\|exec\|compile)\s*\(' -r src/calculator` (also `tests/test_no_eval.py`) | no matches | no matches, and the test passes | PASS |

All 16 run-spec `try_examples` gave exactly the output they promise.

## Known limitations

These are deliberate non-goals, as documented in the README:
- No exponentiation (`2 ** 3`, `2^3`), modulo, variables, functions,
  scientific notation (`1e3`) or implicit multiplication (`2(3)`). Each of these
  is rejected with a clear `ParseError`, exit 1.
- Input comes only from command-line arguments. There is no stdin or REPL mode.
- Arithmetic uses plain Python `int` and `float`, so you get float artefacts such as
  `0.1 + 0.2 = 0.30000000000000004`. Division always gives a float in the library
  (`evaluate('4 / 2')` returns `2.0`). The CLI prints whole-number floats without `.0`.
- Unary plus works (`calc '+2'` prints `2`). The run spec doesn't mention this either way.
- `calc --help` (when it's the only argument) prints usage and exits 0.
- Demo environment: `/workspace` is mounted read-only in the preview. Use
  `COVERAGE_FILE=/tmp/.coverage` and `-p no:cacheprovider`, as above, when running
  pytest there. Otherwise pytest tries to write `.pytest_cache` (and, with `--cov`,
  `.coverage`) into `/workspace`, which causes warnings or errors.
- The workspace contains leftover build artefacts (`build/`, `src/calculator.egg-info/`,
  `.coverage`, `.pytest_cache/`). They are git-ignored, and `build/lib` is identical to
  `src/`, so they don't affect the install.
