from pathlib import Path


ROADMAP = Path(__file__).resolve().parents[1] / "docs" / "architecture" / "GENERICCHESS_THEORY_ROADMAP.md"


def test_current_route_is_the_three_foundational_gates():
    text = ROADMAP.read_text(encoding="utf-8")
    assert "## Current mainline: three foundational gates" in text
    assert "Known-game algorithm equivalence" in text
    assert "Rule-prior baseline strength" in text
    assert "Conditional evolution" in text
    assert "F154 and F155 are explicitly frozen" in text
    assert text.index("Known-game algorithm equivalence") < text.index("Rule-prior baseline strength") < text.index("Conditional evolution")
