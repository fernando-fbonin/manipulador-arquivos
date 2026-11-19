"""Testes de integração do OCR de verdade (PyMuPDF + arquivos de idioma).

Os testes que dependem do idioma inglês só rodam se o arquivo eng.traineddata
existir em data/tessdata. Caso contrário, aparecem como "skipped" (pulados).
"""

from pathlib import Path

import pymupdf
import pytest

from file_manager.domain.exceptions.errors import OcrUnavailableError
from file_manager.infrastructure.config.settings import load_settings
from file_manager.infrastructure.converters.pdf_converter import PdfToMarkdownConverter
from file_manager.infrastructure.ocr.pymupdf_ocr import PymupdfOcrEngine

_TESSDATA_DIR = load_settings().tessdata_dir

requires_english_data = pytest.mark.skipif(
    not (_TESSDATA_DIR / "eng.traineddata").is_file(),
    reason="Arquivo eng.traineddata não encontrado em data/tessdata",
)


def _create_scanned_pdf(path: Path) -> None:
    """Cria um PDF de uma página que contém só uma IMAGEM de texto (sem texto real)."""
    original = pymupdf.open()
    page = original.new_page()
    page.insert_text((72, 120), "Hello OCR World", fontsize=36)
    pixmap = page.get_pixmap(dpi=200)  # transforma a página em imagem

    scanned = pymupdf.open()
    scanned_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
    scanned_page.insert_image(scanned_page.rect, pixmap=pixmap)
    scanned.save(str(path))
    scanned.close()
    original.close()


@requires_english_data
def test_ocr_recognizes_text_in_scanned_pdf(tmp_path: Path):
    source = tmp_path / "escaneado.pdf"
    _create_scanned_pdf(source)

    engine = PymupdfOcrEngine(_TESSDATA_DIR, languages="eng", dpi=200)
    result = engine.recognize_pages(source, [0])

    assert "hello" in result[0].lower()


@requires_english_data
def test_converter_uses_ocr_for_scanned_pdf(tmp_path: Path):
    """Do PDF escaneado ao Markdown, usando o OCR de verdade."""
    source = tmp_path / "escaneado.pdf"
    _create_scanned_pdf(source)
    engine = PymupdfOcrEngine(_TESSDATA_DIR, languages="eng", dpi=200)

    markdown = PdfToMarkdownConverter(ocr_engine=engine, min_text_chars=5).convert(source)

    assert "hello" in markdown.lower()
    assert "texto obtido por OCR" in markdown


def test_ocr_raises_when_language_data_is_missing(tmp_path: Path):
    """Sem os arquivos de idioma, o erro é claro (e acontece antes de abrir o PDF)."""
    engine = PymupdfOcrEngine(tmp_path, languages="por", dpi=200)

    with pytest.raises(OcrUnavailableError):
        engine.recognize_pages(tmp_path / "qualquer.pdf", [0])