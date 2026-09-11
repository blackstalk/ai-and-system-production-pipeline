"""Guards against the intentionally-vulnerable examples/ code ever being
wired into the running application.

examples/ contains deliberately insecure snippets used to demonstrate
what the AI reviewer (see prompts/code-review.md) and Bandit are
expected to catch (see examples/README.md). These tests fail CI if
anything under app/ ever imports from examples/.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _imported_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_app_never_imports_from_examples() -> None:
    app_files = (REPO_ROOT / "app").rglob("*.py")

    offenders = [
        str(f.relative_to(REPO_ROOT))
        for f in app_files
        if any(mod.startswith("examples") for mod in _imported_modules(f))
    ]

    assert offenders == [], f"app/ must never import examples/: {offenders}"


def test_examples_directory_exists_and_is_documented() -> None:
    examples_dir = REPO_ROOT / "examples"
    readme = examples_dir / "README.md"

    assert examples_dir.is_dir()
    assert readme.is_file()
    assert "intentionally" in readme.read_text().lower()
