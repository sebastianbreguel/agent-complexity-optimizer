"""The labeled corpus in tests/cases must match the scanner exactly (see scripts/evaluate_rules.py)."""

from pathlib import Path

from evaluate_rules import evaluate, render


def test_labeled_cases_pass():
    result = evaluate()
    assert result.passed, "\n" + render(result)


def test_stale_todo_is_reported(tmp_path: Path):
    (tmp_path / "case.py").write_text("def f(a, b):\n    for x in a:\n        for y in b:  # todo: nested-loop\n            print(x, y)\n")
    result = evaluate(tmp_path)
    assert not result.passed
    assert result.stale and "change it to `expect:`" in result.stale[0]


def test_unlabeled_finding_is_a_false_positive(tmp_path: Path):
    (tmp_path / "case.py").write_text("def f(a, b):\n    for x in a:\n        for y in b:\n            print(x, y)\n")
    result = evaluate(tmp_path)
    assert result.unexpected == ["case.py:3 unexpected nested-loop"]
    assert result.false_positives["nested-loop"] == 1
