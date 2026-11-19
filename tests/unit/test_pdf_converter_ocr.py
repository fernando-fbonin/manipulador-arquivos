"""Testes do conversor de PDF com OCR.

Usamos um motor de OCR FALSO, que devolve textos prontos. Assim testamos a
lógica (quais páginas vão para o OCR e como o resultado é montado) sem
depender dos arquivos de idioma.
"""

from pathlib import Path

import pymupdf

from file_manager.infrastructure.converters.pdf_converter import PdfToMarkdownConverter


class FakeOcrEngine:
    """OCR falso: devolve um texto pronto para cada página pedida."""

    def __init__(self, texts: dict[int, str]) -> None:
        self._texts = texts
        self.calls: list[list[int]] = []  # registra quais páginas foram pedidas

    def recognize_pages(self, source: Path, page_indexes) -> dict[int, str]:
        self.calls.append(list(page_indexes))
        return {index: self._texts[index] for index in page_indexes}


def _create_pdf(path: Path, page_texts: list[str | None]) -> None:
    """Cria um PDF de teste. Uma entrada None gera uma página em branco."""
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(str(path))
    document.close()


def test_pages_without_text_are_filled_by_ocr(tmp_path: Path):
    """A página 1 tem texto; a página 2 está vazia e deve vir do OCR."""
    source = tmp_path / "misto.pdf"
    _create_pdf(source, ["Hello PDF World", None])
    ocr = FakeOcrEngine({1: "Texto vindo do OCR"})

    markdown = PdfToMarkdownConverter(ocr_engine=ocr, min_text_chars=5).convert(source)

    assert ocr.calls == [[1]]  # só a página 2 (índice 1) foi para o OCR
    assert "Hello PDF World" in markdown
    assert "Texto vindo do OCR" in markdown
    assert "Página 2: texto obtido por OCR" in markdown


def test_ocr_is_not_called_when_all_pages_have_text(tmp_path: Path):
    """PDFs com texto em todas as páginas nunca passam pelo OCR."""
    source = tmp_path / "digital.pdf"
    _create_pdf(source, ["Hello PDF World", "Another page here"])
    ocr = FakeOcrEngine({})

    PdfToMarkdownConverter(ocr_engine=ocr, min_text_chars=5).convert(source)

    assert ocr.calls == []


def test_pages_without_text_are_skipped_when_ocr_is_disabled(tmp_path: Path):
    """Sem motor de OCR, a página vazia é ignorada e a de texto é mantida."""
    source = tmp_path / "misto.pdf"
    _create_pdf(source, ["Hello PDF World", None])

    markdown = PdfToMarkdownConverter(ocr_engine=None, min_text_chars=5).convert(source)

    assert "Hello PDF World" in markdown
    assert "OCR" not in markdown