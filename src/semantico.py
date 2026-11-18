"""Fachada pública e CLI da análise semântica de MorseLang.

A implementação fica em `src.analise_semantica`. Este módulo oferece a API
`analisar(programa)`, `analisar_fonte(fonte)` e a CLI `src/semantico.py`.
"""

import os
import sys

_PROJETO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    # Evita que src/ oculte módulos da biblioteca padrão na execução direta.
    sys.path[0] = _PROJETO_DIR
elif _PROJETO_DIR not in sys.path:
    sys.path.insert(0, _PROJETO_DIR)

from src.analise_semantica import (  # noqa: E402
    AnalisadorSemantico,
    ErroSemantico,
    ResultadoSemantico,
    TOM_MAXIMO,
    TOM_MINIMO,
    TOM_PADRAO,
    VELOCIDADE_PADRAO,
    analisar,
    analisar_fonte,
)

__all__ = [
    "AnalisadorSemantico",
    "ErroSemantico",
    "ResultadoSemantico",
    "TOM_MAXIMO",
    "TOM_MINIMO",
    "TOM_PADRAO",
    "VELOCIDADE_PADRAO",
    "analisar",
    "analisar_fonte",
]


def main(argv: list[str] | None = None) -> int:
    """Executa a CLI canônica de análise semântica."""
    from src.analise_semantica.cli import main as executar

    return executar(argv)


if __name__ == "__main__":
    raise SystemExit(main())
