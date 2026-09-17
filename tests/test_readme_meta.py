"""Claims the repository makes about itself.

The claim tests catch a figure that moved. They cannot catch a test count that drifted, a module
table that no longer matches the package, a README that lost its other language, an example nothing
links, or a placeholder left in the text - and in the two sibling repositories defects of exactly
that class reached the remote before a file like this existed there.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = ("TODO", "FIXME", "XXX", "TKTK", "LOREM", "_EN", "_PT", "Placeholder")


def markdown_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.md")
        if not any(part.startswith(".") or part == "node_modules" for part in path.parts)
    ]


def collected(marker: str) -> int:
    """Tests pytest collects under a marker. There is no total line, so the per-file counts sum."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            marker,
            "-p",
            "no:cacheprovider",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return sum(int(match) for match in re.findall(r"^\S+\.py:\s*(\d+)$", result.stdout, re.M))


def test_no_placeholder_tokens_survive_in_any_markdown() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}: {token}"
        for path in markdown_files()
        for token in PLACEHOLDERS
        if token in path.read_text(encoding="utf-8")
    ]
    assert not offenders, "placeholder tokens left in documentation: " + "; ".join(offenders)


def test_both_readmes_quote_the_number_of_tests_that_exist() -> None:
    """A count corrected in one language and not the other is the same bug."""
    fast = collected("not slow")
    total = fast + collected("slow")

    english = (ROOT / "README.md").read_text(encoding="utf-8")
    portuguese = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")

    quoted = {
        "English total": re.search(r"\*\*(\d[\d,]*) tests,", english),
        "English fast": re.search(r"(\d[\d,]*)\s+of\s+them\s+run\s+in", english),
        "Portuguese total": re.search(r"\*\*(\d[\d,]*) testes,", portuguese),
        "Portuguese fast": re.search(r"(\d[\d,]*)\s+deles\s+rodam\s+em", portuguese),
    }
    for label, match in quoted.items():
        assert match is not None, f"could not find the {label} test count in the README"

    assert int(quoted["English total"].group(1).replace(",", "")) == total
    assert int(quoted["English fast"].group(1).replace(",", "")) == fast
    assert int(quoted["Portuguese total"].group(1).replace(",", "")) == total
    assert int(quoted["Portuguese fast"].group(1).replace(",", "")) == fast

    slow = total - fast
    assert re.search(rf"remaining\s+{slow}\s+re-derive", english), "English slow count"
    assert re.search(rf"Os\s+{slow}\s+restantes\s+re-derivam", portuguese), "Portuguese slow count"


def test_the_module_table_matches_the_package() -> None:
    """A table listing a module that does not exist, or missing one that does, is a lie."""
    packages = {
        path.parent.name
        for path in (ROOT / "src" / "mktlab").rglob("__init__.py")
        if path.parent.name not in {"mktlab", "synth"}
    }
    assert packages, "no modules found, which means this test is not testing anything"
    for readme in ("README.md", "README.pt-BR.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        listed = set(re.findall(r"\[`mktlab\.(\w+)`\]", text))
        assert listed == packages, f"{readme}: table lists {listed}, package has {packages}"


def module_readmes() -> list[Path]:
    """Every README under the package, including the per-topic ones a package may split into."""
    return sorted((ROOT / "src" / "mktlab").rglob("README*.md"))


def test_every_module_readme_is_bilingual() -> None:
    """One language edition going stale is the failure mode, so both are required to exist."""
    found = module_readmes()
    assert found, "no module READMEs found at all, which means this test is not testing anything"
    for readme in found:
        text = readme.read_text(encoding="utf-8")
        assert "*[Português]" in text, f"{readme.relative_to(ROOT)} has no Portuguese section link"
        assert "*[English]" in text, f"{readme.relative_to(ROOT)} has no English section link"
        assert "## Assumptions and limitations" in text, readme.relative_to(ROOT)
        assert "## Premissas e limitações" in text, readme.relative_to(ROOT)


def test_a_split_package_readme_links_its_parts() -> None:
    """A topic document nothing points at is a document nobody finds."""
    for readme in module_readmes():
        if readme.name != "README.md":
            continue
        siblings = [
            other.name for other in readme.parent.glob("README*.md") if other.name != "README.md"
        ]
        text = readme.read_text(encoding="utf-8")
        for sibling in siblings:
            assert sibling in text, f"{readme.relative_to(ROOT)} does not link {sibling}"


def test_every_module_readme_is_linked_from_both_root_readmes() -> None:
    """The root table is the only route into them, so a module document it omits is orphaned."""
    for readme in ("README.md", "README.pt-BR.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        for module in module_readmes():
            relative = module.relative_to(ROOT).as_posix()
            assert relative in text, f"{readme} does not link {relative}"


def test_every_example_is_linked_from_both_readmes() -> None:
    """An example nothing references is an example nobody runs."""
    scripts = {path.name for path in (ROOT / "examples").glob("*.py")}
    assert scripts, "no examples found, which means this test is not testing anything"
    for readme in ("README.md", "README.pt-BR.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        for script in scripts:
            assert script in text, f"{readme} does not link examples/{script}"


def test_the_disclaimer_is_bilingual_and_names_the_invented_labels() -> None:
    """It is the load-bearing document of the repository, so its contract is tested."""
    text = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    assert "# Disclaimer" in text
    assert "# Aviso" in text
    for label in ("social-pago", "email", "busca-generica", "retargeting", "busca-marca", "UF-01"):
        assert label in text, f"{label} is not declared as an invented label"


def test_the_disclaimer_declares_the_intent_column_as_invented() -> None:
    """The one column no real account has, and the reason the repository can claim anything."""
    text = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    assert "`intent`" in text
    assert "invented" in text
    assert "inventada" in text


def test_both_root_readmes_link_the_disclaimer() -> None:
    for readme in ("README.md", "README.pt-BR.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        assert "DISCLAIMER.md" in text, f"{readme} does not link the disclaimer"


def test_the_two_root_readmes_point_at_each_other() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    portuguese = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")
    assert "README.pt-BR.md" in english
    assert "README.md" in portuguese


def test_every_channel_in_the_package_is_named_in_the_disclaimer() -> None:
    """A channel added to the generator and not declared as invented is the failure to catch."""
    from mktlab.synth import CHANNELS

    text = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    for profile in CHANNELS:
        assert profile.channel in text, f"{profile.channel} is not declared in the disclaimer"


def test_the_roadmap_exists_and_says_what_is_deliberately_missing() -> None:
    """A roadmap that only lists what was built reads as a claim of completeness."""
    text = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    assert "What is deliberately not here" in text
    assert "Still open" in text
