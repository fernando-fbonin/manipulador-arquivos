"""Motor de OCR baseado no PyMuPDF (camada de INFRAESTRUTURA).

O PyMuPDF já traz o motor Tesseract embutido. A única coisa externa de que
ele precisa são os arquivos de idioma (.traineddata), por exemplo
por.traineddata para português.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from file_manager.domain.exceptions.errors import ConversionError, OcrUnavailableError


class PymupdfOcrEngine:
    """Reconhece o texto de páginas escaneadas usando o PyMuPDF."""

    def __init__(self, tessdata_dir: Path, languages: str, dpi: int = 300) -> None:
        """Guarda a configuração do OCR.

        Args:
            tessdata_dir: pasta com os arquivos .traineddata.
            languages: idiomas separados por "+", por exemplo "por+eng".
            dpi: resolução usada para "fotografar" cada página. Valores
                maiores aumentam a precisão e o tempo de processamento.
        """
        self._tessdata_dir = tessdata_dir
        self._languages = languages
        self._dpi = dpi

    def recognize_pages(self, source: Path, page_indexes: Sequence[int]) -> dict[int, str]:
        """Executa o OCR nas páginas indicadas (numeração a partir de zero).

        Raises:
            OcrUnavailableError: se faltar algum arquivo de idioma.
            ConversionError: se o PDF não abrir ou o OCR falhar em uma página.
        """
        # Validamos ANTES de abrir o PDF, para dar uma mensagem clara.
        self._ensure_language_data()

        # Import "tardio": só carrega a biblioteca quando o OCR é realmente usado.
        import pymupdf

        try:
            document = pymupdf.open(str(source))
        except Exception as error:
            raise ConversionError(f"Não foi possível abrir o PDF para o OCR: {error}") from error

        recognized: dict[int, str] = {}
        # O "with" garante que o PDF será fechado ao final, mesmo se houver erro.
        with document:
            for page_index in page_indexes:
                try:
                    recognized[page_index] = self._recognize_page(document[page_index])
                except Exception as error:
                    raise ConversionError(
                        f"Falha no OCR da página {page_index + 1}: {error}"
                    ) from error
        return recognized

    def _recognize_page(self, page) -> str:
        """Executa o OCR em uma página e devolve o texto reconhecido."""
        # get_textpage_ocr "fotografa" a página na resolução pedida, aplica o
        # OCR e devolve um objeto com o texto encontrado.
        #   full=True  -> reconhece a página inteira (não só as imagens)
        #   tessdata   -> pasta com os arquivos de idioma
        text_page = page.get_textpage_ocr(
            language=self._languages,
            dpi=self._dpi,
            full=True,
            tessdata=str(self._tessdata_dir),
        )
        raw_text = page.get_text("text", textpage=text_page)
        return self._clean_text(raw_text)

    def _ensure_language_data(self) -> None:
        """Confere se existe um arquivo .traineddata para cada idioma pedido."""
        missing = [
            f"{language}.traineddata"
            for language in self._languages.split("+")
            if not (self._tessdata_dir / f"{language}.traineddata").is_file()
        ]
        if missing:
            raise OcrUnavailableError(
                f"Arquivos de idioma do OCR não encontrados em '{self._tessdata_dir}': "
                f"{', '.join(missing)}. Baixe-os conforme a seção OCR do README."
            )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Limpa o texto do OCR: tira espaços no fim das linhas e linhas vazias demais."""
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned = "\n".join(lines)
        # Três ou mais quebras de linha seguidas viram duas (um parágrafo).
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()