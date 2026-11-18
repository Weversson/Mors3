"""Visualização web local de MorseLang.

O pacote oferece a API JSON (`analisar`) e o servidor HTTP (`criar_servidor`)
que serve a página estática em `web/`.
"""

from .api import LIMITE_PADRAO, analisar, analisar_timeline
from .servidor import ServidorVisual, criar_servidor

__all__ = [
    "LIMITE_PADRAO",
    "ServidorVisual",
    "analisar",
    "analisar_timeline",
    "criar_servidor",
]
