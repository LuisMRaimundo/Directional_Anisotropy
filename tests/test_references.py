"""Bibliografia alinhada com métodos implementados."""

from anisotropia.references import REFERENCES, format_references_report_markdown


def test_references_count_and_removed_weickert():
    assert len(REFERENCES) == 9
    blob = " ".join(r.citation for r in REFERENCES)
    assert "Weickert" not in blob


def test_references_include_newly_used_methods():
    blob = " ".join(r.citation for r in REFERENCES)
    assert "MusicXML" in blob
    assert "Rousseeuw" in blob
    assert "Marvin" in blob


def test_report_references_markdown():
    lines = format_references_report_markdown()
    assert any("Structure tensor" in ln for ln in lines)
    assert any("Robust scale" in ln for ln in lines)
    assert not any("Weickert" in ln for ln in lines)
