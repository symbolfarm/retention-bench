"""Prose claims must still match the code they describe.

``tests/test_docs_links.py`` proves a cited *path* exists. It cannot prove the
prose about that path is still true, and the learning guide in ``pages/`` is
built almost entirely out of such claims: it restates ε, the schedule size, and
the name of the function that implements each design decision. Those are
exactly the statements that rot silently — nothing breaks at runtime when ε is
retuned and six prose files keep quoting the old number.

Three checks, one per class of claim the guide makes:

* ``test_source_anchors_resolve`` — every ``source:`` ref in ``pages/map.js``
  names a real Python symbol or a real markdown heading. The guide originally
  used line-number anchors (``system.py:318``); those were correct on the day
  they were written and had no way to stay correct, which is why the refs are
  symbol-shaped now and why this test exists to keep them honest.
* ``test_epsilon_claims_match_code`` / ``test_r_max_claims_match_task`` — the
  two numeric constants the docs and pages quote back at the reader, checked
  against the source of truth rather than against each other.
* ``test_page_relative_links_resolve`` — the HTML equivalent of the markdown
  link check, so a rename inside ``pages/`` cannot dangle unnoticed.

Deliberately *not* here: any check that the explanatory prose matches the
reference docs word for word. The guide is a different register for a different
reader, and forcing the two to converge would destroy the thing that makes it
useful. Only the facts are shared, so only the facts are enforced.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from retention_bench.scoring import EPSILON

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES = REPO_ROOT / "pages"
TASK_MODULE = REPO_ROOT / "retention_bench" / "tasks" / "symbolic_associative_retention.py"

EXCLUDED_PREFIXES = ("docs/archive/", "history/")


# --- source anchors -------------------------------------------------------- #

# source: {path: "...", symbol: "..."} | {path: "...", heading: "..."}
SOURCE_RE = re.compile(
    r'source:\s*\{path:\s*"([^"]+)",\s*(symbol|heading):\s*"((?:[^"\\]|\\.)*)"\}'
)

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$")


def _map_js_anchors() -> list[tuple[str, str, str]]:
    text = (PAGES / "map.js").read_text(encoding="utf-8")
    found = [(p, k, n.replace('\\"', '"')) for p, k, n in SOURCE_RE.findall(text)]
    assert found, "pages/map.js exposes no source: refs — has the shape changed?"
    return found


def _python_symbols(path: Path) -> set[str]:
    """Every def/class/assignment name in the module, at any nesting depth."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _markdown_headings(path: Path) -> set[str]:
    """Heading text, skipping fenced blocks (metrics.md has `#` comments in shell)."""
    headings: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if m := HEADING_RE.match(line):
            headings.add(m.group(1))
    return headings


@pytest.mark.parametrize(
    "rel_path,kind,name", _map_js_anchors(), ids=lambda v: str(v)[:40]
)
def test_source_anchors_resolve(rel_path: str, kind: str, name: str) -> None:
    target = REPO_ROOT / rel_path
    assert target.exists(), f"pages/map.js anchors {rel_path}, which does not exist"

    if kind == "symbol":
        symbols = _python_symbols(target)
        assert name in symbols, (
            f"pages/map.js claims {rel_path} defines `{name}`, but it does not. "
            f"Either the symbol was renamed (update the anchor) or the decision "
            f"it documents has moved."
        )
    else:
        headings = _markdown_headings(target)
        assert name in headings, (
            f"pages/map.js anchors {rel_path} heading '{name}', which is gone. "
            f"The page also builds its deep link from this text, so the URL "
            f"fragment is now dead too. Headings present: {sorted(headings)}"
        )


# --- numeric claims -------------------------------------------------------- #

def _prose_files() -> list[Path]:
    files = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").glob("*.md"))]
    files += sorted(PAGES.glob("*.html")) + sorted(PAGES.glob("*.js"))
    return [
        f for f in files
        if not f.relative_to(REPO_ROOT).as_posix().startswith(EXCLUDED_PREFIXES)
    ]


# "ε = 0.05 × r_max", "`ε = 0.05 × r_max`" — the decimal form, wherever quoted.
EPSILON_DECIMAL_RE = re.compile(r"ε\s*=\s*([0-9.]+)\s*×\s*r_max")
# "5% of the task's achievable ...", "asking 5% of a fully-scored task"
EPSILON_PERCENT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s+of\s+(?:the\s+)?(?:task|score|a\s+fully)")


def test_epsilon_claims_match_code() -> None:
    expected_decimal = float(EPSILON)
    expected_percent = EPSILON * 100
    wrong: list[str] = []
    seen = 0

    for f in _prose_files():
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(REPO_ROOT).as_posix()
        for raw in EPSILON_DECIMAL_RE.findall(text):
            seen += 1
            if float(raw) != expected_decimal:
                wrong.append(f"{rel}: 'ε = {raw} × r_max' but EPSILON is {expected_decimal}")
        for raw in EPSILON_PERCENT_RE.findall(text):
            seen += 1
            if float(raw) != expected_percent:
                wrong.append(f"{rel}: '{raw}% of ...' but EPSILON is {expected_percent}%")

    assert seen, (
        "No ε claim matched either pattern. The prose was probably reworded — "
        "re-point the regexes rather than deleting the check."
    )
    assert not wrong, "Stale ε claims:\n  " + "\n  ".join(wrong)


def _task_r_max_literals() -> tuple[tuple[int, int], set[tuple[int, int]]]:
    """The task's declared ``r_max`` fractions, as (default, all_declared).

    Read from source, not from the evaluated float: 64/112 reduces to 4/7, so
    the denominator the docs quote ("the 112-instance schedule") is not
    recoverable from the value alone.

    ``all_declared`` is wider than the class attribute on purpose. The task
    module's own docstring names the smaller pre-RB-16 shape (``r_max = 16/26``,
    still regenerable via ``num_attributes=2, objects_per_attribute=4``), and
    ``docs/associative-curriculum.md`` legitimately quotes it when explaining
    what published numbers refer to. Sourcing the allow-list from the module
    means a doc may cite any schedule the code still documents — and nothing
    else. Retire a shape in the code and the prose quoting it fails here.
    """
    text = TASK_MODULE.read_text(encoding="utf-8")
    declared = {
        (int(a), int(b)) for a, b in re.findall(r"r_max\s*=\s*([0-9]+)\s*/\s*([0-9]+)", text)
    }
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "r_max" for t in node.targets):
            continue
        v = node.value
        if (
            isinstance(v, ast.BinOp)
            and isinstance(v.op, ast.Div)
            and isinstance(v.left, ast.Constant)
            and isinstance(v.right, ast.Constant)
        ):
            default = (int(v.left.value), int(v.right.value))
            return default, declared | {default}
    pytest.fail(f"No `r_max = <int> / <int>` literal found in {TASK_MODULE.name}")


# "r_max = 64/112", "64 / 112"
R_MAX_FRACTION_RE = re.compile(r"r_max\s*=\s*([0-9]+)\s*/\s*([0-9]+)")
# "the default 112-instance schedule", "the real 112-instance default"
INSTANCE_COUNT_RE = re.compile(r"([0-9]+)-instance")

# Instance counts that are illustrations rather than claims about a real
# schedule. The worked run in pages/ is a six-step toy and says so in its lede.
ILLUSTRATIVE_INSTANCE_COUNTS = {6}


def test_r_max_claims_match_task() -> None:
    default, declared = _task_r_max_literals()
    allowed_counts = {den for _, den in declared} | ILLUSTRATIVE_INSTANCE_COUNTS
    wrong: list[str] = []
    seen = 0
    saw_default = False

    for f in _prose_files():
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(REPO_ROOT).as_posix()
        for a, b in R_MAX_FRACTION_RE.findall(text):
            seen += 1
            if (int(a), int(b)) == default:
                saw_default = True
            elif (int(a), int(b)) not in declared:
                wrong.append(
                    f"{rel}: 'r_max = {a}/{b}' is not a schedule "
                    f"{TASK_MODULE.name} declares (default {default[0]}/{default[1]})"
                )
        for raw in INSTANCE_COUNT_RE.findall(text):
            seen += 1
            if int(raw) not in allowed_counts:
                wrong.append(
                    f"{rel}: '{raw}-instance' matches no declared schedule "
                    f"(default is {default[1]})"
                )

    assert seen, "No r_max/schedule-size claim matched — re-point the regexes."
    assert saw_default, (
        f"Nothing quotes the default schedule {default[0]}/{default[1]}; the "
        f"check would pass vacuously if the docs stopped naming it."
    )
    assert not wrong, "Stale schedule-size claims:\n  " + "\n  ".join(wrong)


# --- HTML links ------------------------------------------------------------ #

HREF_RE = re.compile(r'href="([^"]+)"')


@pytest.mark.parametrize(
    "page", sorted(PAGES.glob("*.html")), ids=lambda p: p.name
)
def test_page_relative_links_resolve(page: Path) -> None:
    broken: list[str] = []
    for target in HREF_RE.findall(page.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part:
            continue
        if not (page.parent / path_part).resolve().exists():
            broken.append(target)

    assert not broken, (
        f"pages/{page.name} has {len(broken)} dangling link(s): " + ", ".join(broken)
    )
