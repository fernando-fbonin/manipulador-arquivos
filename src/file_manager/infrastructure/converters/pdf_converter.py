"""Conversor de PDF para Markdown (camada de INFRAESTRUTURA).

Usa a biblioteca pymupdf4llm, que detecta títulos, listas e tabelas e gera
um Markdown estruturado.

Modo clássico: as versões novas da biblioteca usam por padrão um "modo
layout" (com modelo de inteligência artificial e arquivos compilados extras).
Aqui desativamos esse modo e usamos o clássico, que é mais leve e não
depende desses arquivos extras.

OCR: páginas escaneadas (só imagem) não têm texto para extrair. Elas são
detectadas pela quantidade de texto e, se houver um motor de OCR configurado,
reconhecidas por ele. PDFs com texto nunca passam pelo OCR.
"""

from __future__ import annotations

from pathlib import Path

from file_manager.application.interfaces.ocr_engine import OcrEngine
from file_manager.domain.exceptions.errors import ConversionError

# Separador entre páginas no Markdown gerado.
_PAGE_SEPARATOR = "\n\n-----\n\n"


class PdfToMarkdownConverter:
    """Converte arquivos .pdf em Markdown, com OCR opcional para páginas escaneadas."""

    supported_extensions = frozenset({".pdf"})

    def __init__(self, ocr_engine: OcrEngine | None = None, min_text_chars: int = 20) -> None:
        """Recebe as dependências já prontas.

        Args:
            ocr_engine: motor de OCR. Se for None, o OCR fica desligado e
                páginas escaneadas simplesmente não geram texto.
            min_text_chars: páginas com MENOS caracteres que isto são
                tratadas como escaneadas.
        """
        self._ocr_engine = ocr_engine
        self._min_text_chars = min_text_chars

    def convert(self, source: Path) -> str:
        page_texts = self._extract_page_texts(source)

        # Se o resultado não veio dividido por página, devolve como está.
        if isinstance(page_texts, str):
            return page_texts

        ocr_texts = self._recognize_pages_without_text(source, page_texts)
        return self._assemble(page_texts, ocr_texts)

    def _extract_page_texts(self, source: Path) -> list[str] | str:
        """Converte o PDF e devolve o Markdown de cada página (lista com uma entrada por página)."""
        try:
            # Import "tardio": a biblioteca é pesada. Importando aqui dentro, os
            # outros recursos (como separar PDF) continuam rápidos para abrir.
            import pymupdf4llm

            # getattr busca o comando use_layout se ele existir. Assim, o código
            # também funciona com versões antigas da biblioteca, que não o têm
            # (e que já usam o modo clássico).
            use_layout = getattr(pymupdf4llm, "use_layout", None)
            if use_layout is not None:
                use_layout(False)  # False = modo clássico

            # page_chunks=True devolve uma lista com um dicionário por página;
            # a chave "text" contém o Markdown da página.
            chunks = pymupdf4llm.to_markdown(str(source), page_chunks=True)
        except Exception as error:
            # Arquivo corrompido, protegido por senha, biblioteca bloqueada etc.
            raise ConversionError(f"Não foi possível converter o PDF: {error}") from error

        if isinstance(chunks, str):
            return chunks
        return [str(chunk.get("text", "")).strip() for chunk in chunks]

    def _recognize_pages_without_text(
        self, source: Path, page_texts: list[str]
    ) -> dict[int, str]:
        """Roda o OCR somente nas páginas que quase não têm texto."""
        if self._ocr_engine is None:
            return {}

        pages_without_text = [
            index for index, text in enumerate(page_texts) if len(text) < self._min_text_chars
        ]
        if not pages_without_text:
            return {}  # PDF com texto em todas as páginas: não precisa de OCR

        return self._ocr_engine.recognize_pages(source, pages_without_text)

    @staticmethod
    def _assemble(page_texts: list[str], ocr_texts: dict[int, str]) -> str:
        """Junta o texto das páginas, na ordem original."""
        parts: list[str] = []
        for index, text in enumerate(page_texts):
            ocr_text = ocr_texts.get(index, "")
            if ocr_text:
                # Um comentário HTML não aparece na visualização do Markdown,
                # mas deixa claro no arquivo que esta página veio do OCR.
                parts.append(f"<!-- Página {index + 1}: texto obtido por OCR -->\n\n{ocr_text}")
            elif text:
                parts.append(text)
        return _PAGE_SEPARATOR.join(parts)