"""Fachada pública e CLI da análise léxica de MorseLang.

A implementação fica no pacote `src.analise_lexica`; este módulo mantém os
imports históricos da E2 (`ErroLexico`, `TokenInfo`, `criar_lexer`, `analisar`)
e a execução direta de `src/lexico.py`.
"""

import os
import sys

_PROJETO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    # Na execução direta, src/ ocupa sys.path[0] e faria `ast` resolver para
    # src/ast.py em vez do módulo da biblioteca padrão. A raiz do projeto
    # substitui essa entrada, como já ocorria na versão anterior do módulo.
    sys.path[0] = _PROJETO_DIR
elif _PROJETO_DIR not in sys.path:
    sys.path.insert(0, _PROJETO_DIR)

from src.analise_lexica import (  # noqa: E402
    ErroLexico,
    TokenInfo,
    analisar,
    criar_lexer,
    iterar_tokens,
)

__all__ = [
    "ErroLexico",
    "TokenInfo",
    "analisar",
    "criar_lexer",
    "iterar_tokens",
]


def main(argv: list[str] | None = None) -> int:
    """Executa a CLI canônica de análise léxica."""
    from src.analise_lexica.cli import main as executar

    return executar(argv)


if __name__ == "__main__":
    raise SystemExit(main())
