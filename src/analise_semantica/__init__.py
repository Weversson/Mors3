"""Análise semântica modular de MorseLang.

O pacote valida a AST produzida pelo parser e expõe um resultado com o tom e a
velocidade efetivos, incluindo os padrões da linguagem. A execução e a geração
de arquivos Morse/WAV não fazem parte desta etapa.
"""

from .analisador import AnalisadorSemantico, analisar, analisar_fonte
from .erros import ErroSemantico
from .modelo import (
    TOM_MAXIMO, TOM_MINIMO, TOM_PADRAO, VELOCIDADE_PADRAO,
    ResultadoSemantico,
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
