"""Execução headless de MorseLang: expansão para uma timeline de eventos.

A execução não gera arquivos. Ela valida a fonte até a semântica e transforma
as emissões em tons e silêncios com tempos em milissegundos.
"""

from .erros import ErroExecucao
from .expansor import expandir, expandir_texto, unidade_ms
from .modelo import (
    MOTIVOS_SILENCIO, TIPOS_EVENTO, UNIDADE_BASE_MS, Evento, Timeline,
    texto_decimal,
)

__all__ = [
    "Evento",
    "ErroExecucao",
    "MOTIVOS_SILENCIO",
    "TIPOS_EVENTO",
    "Timeline",
    "UNIDADE_BASE_MS",
    "expandir",
    "expandir_texto",
    "texto_decimal",
    "unidade_ms",
]
