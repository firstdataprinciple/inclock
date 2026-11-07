"""Regression: every known word in tests/sample.pdf — including chart labels that live
only inside an image — must appear in the extraction output.  Run: pytest -q"""
from pathlib import Path

from app.pipeline import extract

SAMPLE = Path(__file__).parent / "sample.pdf"
EXPECTED = ["Annual", "Report:", "Statistics", "Overview", "native", "extracted.", "25%", "Quarterly",
            "Revenue", "2025", "42M", "58M", "73M", "91M", "Q1", "Q2", "Q3", "Q4", "Figure", "chart"]


def test_no_word_lost():
    r = extract(str(SAMPLE))
    got = {t.lower() for p in r["pages"] for i in p["items"] for t in [i["text"], *[a["text"] for a in i.get("alts", [])]]}
    missing = [w for w in EXPECTED if w.lower() not in got]
    assert not missing, f"missing: {missing}"
    full = r["text"]
    assert "Q4" in full and "42M" in full  # also present in the exported text, not just the boxes
