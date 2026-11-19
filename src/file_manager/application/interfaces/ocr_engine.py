"""Contrato para motores de OCR (camada de APLICAÇÃO).

OCR (Reconhecimento Óptico de Caracteres) transforma a imagem de uma página
escaneada em texto. O conversor de PDF só conhece este contrato: qual
biblioteca faz o reconhecimento é um detalhe da infraestrutura.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class OcrEngine(Protocol):
    """Contrato: quem reconhece o texto de páginas escaneadas de um PDF."""

    def recognize_pages(self, source: Path, page_indexes: Sequence[int]) -> dict[int, str]:
        """Executa o OCR nas páginas indicadas.

        Args:
            source: caminho do PDF.
            page_indexes: números das páginas a reconhecer, contando a
                partir de ZERO (a primeira página é 0).

        Returns:
            Dicionário {número da página: texto reconhecido}.
        """
        ...