"""Análise léxica modular de MorseLang.

A gramática ANTLR em `gramatica/MorseLang.g4` é a fonte de verdade para os
tipos de token. Este pacote expõe o lexer configurado, a iteração de tokens e
a análise completa, mantendo a CLI separada em `src.analise_lexica.cli`.
"""

from .analisador import analisar, criar_lexer, iterar_tokens
from .erros import ErroLexico
from .modelo import TokenInfo

__all__ = [
    "ErroLexico",
    "TokenInfo",
    "analisar",
    "criar_lexer",
    "iterar_tokens",
]
