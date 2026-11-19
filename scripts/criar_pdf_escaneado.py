"""Cria uma cópia "escaneada" de um PDF, para testar o OCR.

Cada página do PDF original é transformada em imagem e colocada em um PDF
novo, sem nenhum texto. É como se o documento tivesse sido escaneado.

Uso (na raiz do projeto, com o .venv ativo):

    python scripts\\criar_pdf_escaneado.py "Teste Manual 1.pdf"
    python scripts\\criar_pdf_escaneado.py "Teste Manual 1.pdf" 5

O segundo argumento (opcional) é o máximo de páginas a copiar. Padrão: 3.
Se o arquivo não for encontrado, o script procura em data/library.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

LIBRARY_DIR = Path("data") / "library"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: python scripts\\criar_pdf_escaneado.py <arquivo.pdf> [máximo de páginas]")
        return 1

    source_path = Path(argv[1])
    if not source_path.is_file():
        source_path = LIBRARY_DIR / argv[1]
    if not source_path.is_file():
        print(f"Arquivo não encontrado: {argv[1]}")
        return 1

    max_pages = int(argv[2]) if len(argv) > 2 else 3
    output_path = source_path.with_name(f"{source_path.stem}_escaneado.pdf")

    with pymupdf.open(str(source_path)) as original, pymupdf.open() as scanned:
        for index in range(min(max_pages, len(original))):
            page = original[index]

            # "Fotografa" a página original em 200 dpi...
            pixmap = page.get_pixmap(dpi=200)

            # ...e coloca a imagem, e só ela, em uma página nova.
            new_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pixmap)

        scanned.save(str(output_path))

    print(f"PDF escaneado criado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))