"""Geração dos arquivos finais a partir da timeline de execução.

Esta etapa é separada da execução: a timeline continua sendo a única fonte de
tempos e símbolos, e os geradores apenas a serializam em texto Morse ou PCM/WAV.
"""

from .audio import (
    AMOSTRA_PADRAO,
    escrever_wav,
    gerar_pcm,
    gerar_wav,
)
from .erros import ErroGeracao
from .texto import (
    SEPARADOR_CARACTERES,
    SEPARADOR_EMISSOES,
    SEPARADOR_PALAVRAS,
    escrever_morse,
    gerar_morse,
    morse_de_texto,
)

__all__ = [
    "AMOSTRA_PADRAO",
    "SEPARADOR_CARACTERES",
    "SEPARADOR_EMISSOES",
    "SEPARADOR_PALAVRAS",
    "ErroGeracao",
    "escrever_morse",
    "escrever_wav",
    "gerar_morse",
    "gerar_pcm",
    "gerar_wav",
    "morse_de_texto",
]
