"""Tests for the command-line interface (calculator.cli and python -m calculator)."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from calculator.cli import USAGE, format_result, main
from calculator.errors import CalculatorError

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

HAS_INT_MAX_STR_DIGITS = hasattr(sys, "get_int_max_str_digits")


# ---------------------------------------------------------------------------
# format_result
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (11, "11"),
        (0, "0"),
        (-7, "-7"),
        (2.0, "2"),
        (-2.0, "-2"),
        (-0.0, "0"),
        (0.0, "0"),
        (3.5, "3.5"),
        (-3.5, "-3.5"),
        (0.1 + 0.2, "0.30000000000000004"),
        (1e20, "1e+20"),
        (float("inf"), "inf"),
        (float("-inf"), "-inf"),
        (float(2**53), repr(float(2**53))),
        (-float(2**53), repr(-float(2**53))),
        (float(2**53 - 1), str(2**53 - 1)),
        (2**60, str(2**60)),
    ],
)
def test_format_result(value, expected):
    assert format_result(value) == expected


def test_format_result_float_2_pow_53_uses_repr():
    assert format_result(float(2**53)) == "9007199254740992.0"


def test_format_result_nan_uses_repr():
    assert format_result(float("nan")) == "nan"


def test_format_result_division_result():
    # Integral floats are shown without a trailing '.0'.
    assert format_result(4 / 2) == "2"


@pytest.fixture
def default_int_digit_limit():
    """Force the default int max-str-digits limit for the duration of a test."""
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield 4300
    finally:
        sys.set_int_max_str_digits(old)


@pytest.mark.skipif(
    not HAS_INT_MAX_STR_DIGITS, reason="int max-str-digits limit unsupported"
)
def test_format_result_huge_int_raises_calculator_error(default_int_digit_limit):
    huge = 10 ** (default_int_digit_limit + 10)
    with pytest.raises(CalculatorError, match="^result too large to display$"):
        format_result(huge)


@pytest.mark.skipif(
    not HAS_INT_MAX_STR_DIGITS, reason="int max-str-digits limit unsupported"
)
def test_main_huge_result_reports_error(default_int_digit_limit, capsys):
    # 10**4400 via repeated multiplication stays an int expression.
    expr = " * ".join(["10000000000"] * 440)  # (10**10)**440 = 10**4400
    rc = main([expr])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert err == "calc: error: result too large to display\n"


# ---------------------------------------------------------------------------
# main() in-process
# ---------------------------------------------------------------------------


def test_main_basic_expression(capsys):
    rc = main(["2 + 3 * (4 - 1)"])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == "11\n"
    assert err == ""


def test_main_joins_multiple_arguments(capsys):
    rc = main(["2", "+", "3"])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == "5\n"
    assert err == ""


def test_main_leading_minus_is_not_an_option(capsys):
    rc = main(["-3+5"])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == "2\n"
    assert err == ""


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("8 / 4 / 2", "1\n"),
        ("7 / 2", "3.5\n"),
        ("-3 + 5", "2\n"),
        ("4 / 2", "2\n"),
        ("((2 + 3) * (4 - (1 + 1)))", "10\n"),
        ("--3", "3\n"),
        ("+3", "3\n"),
        ("0.1 + 0.2", "0.30000000000000004\n"),
    ],
)
def test_main_outputs(expr, expected, capsys):
    rc = main([expr])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == expected
    assert err == ""


def test_main_division_by_zero(capsys):
    rc = main(["1 / 0"])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert "division by zero" in err.lower()
    assert err == "calc: error: division by zero\n"


def test_main_parse_error(capsys):
    rc = main(["(1 + 2"])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert err.startswith("calc: error:")
    assert err.endswith("\n")


def test_main_unexpected_character_message(capsys):
    rc = main(["2 $ 3"])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert "unexpected character '$' (at position 2)" in err


def test_main_syntax_error_reported_before_division(capsys):
    rc = main(["1 / 0 +"])
    _, err = capsys.readouterr()
    assert rc == 1
    assert "division by zero" not in err
    assert err.startswith("calc: error:")


def test_main_empty_string_argument_is_calculator_error(capsys):
    rc = main([""])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert err.startswith("calc: error:")


def test_main_no_arguments_prints_usage(capsys):
    rc = main([])
    out, err = capsys.readouterr()
    assert rc == 2
    assert out == ""
    assert err == USAGE + "\n"
    assert err.startswith("usage:")


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_main_help(flag, capsys):
    rc = main([flag])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == USAGE + "\n"
    assert err == ""


def test_main_help_flag_only_when_sole_argument(capsys):
    # '-h' combined with other arguments is treated as part of an expression.
    rc = main(["-h", "1"])
    out, err = capsys.readouterr()
    assert rc == 1
    assert out == ""
    assert err.startswith("calc: error:")


def test_main_defaults_to_sys_argv(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["calc", "6", "*", "7"])
    rc = main()
    out, err = capsys.readouterr()
    assert rc == 0
    assert out == "42\n"
    assert err == ""


def test_main_defaults_to_sys_argv_empty(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["calc"])
    rc = main()
    _, err = capsys.readouterr()
    assert rc == 2
    assert err == USAGE + "\n"


def test_main_does_not_catch_non_calculator_errors(monkeypatch):
    import calculator.cli as cli

    def boom(_expr):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(cli, "evaluate", boom)
    with pytest.raises(RuntimeError, match="unexpected"):
        cli.main(["1"])


def test_usage_text():
    assert USAGE == (
        "usage: calc '<expression>'  "
        "(quote the expression; exit codes: 0 ok, 1 calculator error, 2 usage)"
    )


def test_cli_does_not_use_argparse():
    source = (SRC_DIR / "calculator" / "cli.py").read_text(encoding="utf-8")
    assert "argparse" not in source


# ---------------------------------------------------------------------------
# python -m calculator, in-process (for coverage of __main__.py)
# ---------------------------------------------------------------------------


def test_dunder_main_in_process(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["calculator", "2 + 3"])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("calculator", run_name="__main__")
    out, _ = capsys.readouterr()
    assert info.value.code == 0
    assert out == "5\n"


# ---------------------------------------------------------------------------
# python -m calculator, subprocess
# ---------------------------------------------------------------------------


def _run_module(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_DIR) if not existing else str(SRC_DIR) + os.pathsep + existing
    )
    return subprocess.run(
        [sys.executable, "-m", "calculator", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_subprocess_success():
    proc = _run_module("2 + 3 * (4 - 1)")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "11"
    assert proc.stderr == ""


def test_subprocess_nested_parentheses():
    proc = _run_module("((2 + 3) * (4 - (1 + 1)))")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "10"


@pytest.mark.parametrize("expr", ["1 / 0", "", "2 +", "2 $ 3"])
def test_subprocess_calculator_errors(expr):
    proc = _run_module(expr)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("calc: error:")
    assert "Traceback" not in proc.stderr


def test_subprocess_division_by_zero_message():
    proc = _run_module("1 / 0")
    assert proc.returncode == 1
    assert "calc: error: division by zero" in proc.stderr


def test_subprocess_unexpected_character_message():
    proc = _run_module("2 $ 3")
    assert proc.returncode == 1
    assert "unexpected character '$' (at position 2)" in proc.stderr


def test_subprocess_no_arguments_is_usage_error():
    proc = _run_module()
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert proc.stderr.startswith("usage:")
    assert "Traceback" not in proc.stderr
