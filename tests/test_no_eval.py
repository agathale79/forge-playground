"""Static guard: the calculator source must never call eval/exec/compile/__import__."""

import ast
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "calculator"
FORBIDDEN = {"eval", "exec", "compile", "__import__"}


def _source_files():
    return sorted(SRC_DIR.rglob("*.py"))


def test_sources_found():
    assert SRC_DIR.is_dir(), SRC_DIR
    assert len(_source_files()) >= 1


def test_no_forbidden_calls():
    offenders = []
    scanned = 0
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scanned += 1
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN
            ):
                offenders.append(f"{path.name}:{node.lineno}: {node.func.id}()")
    assert scanned >= 1
    assert offenders == [], offenders
