"""Geração de áudio PCM/WAV a partir da timeline de execução.

Os tempos e o tom vêm da ``Timeline``, então o áudio gerado aqui é o mesmo som
que a interface reproduz com Web Audio. A conversão usa apenas a biblioteca
padrão: ``array`` para os samples e ``wave`` para o contêiner WAV.
"""

import array
from decimal import Decimal, InvalidOperation
import io
import math
from pathlib import Path
import wave

from src.execucao import Timeline

from .erros import ErroGeracao

AMOSTRA_PADRAO = 44_100
AMPLITUDE_PADRAO = 0.5
RAMPA_MS_PADRAO = 5.0
VALOR_MAXIMO = 32_767


def _validar_opcoes(
    taxa_amostragem: int,
    amplitude: float,
    rampa_ms: float | int | Decimal,
) -> tuple[int, float, Decimal]:
    if (isinstance(taxa_amostragem, bool)
            or not isinstance(taxa_amostragem, int)
            or taxa_amostragem <= 0):
        raise ValueError("taxa_amostragem deve ser um inteiro positivo")
    if not isinstance(amplitude, (int, float)) or isinstance(amplitude, bool):
        raise ValueError("amplitude deve ser um número")
    amplitude = float(amplitude)
    if not math.isfinite(amplitude) or not 0 < amplitude <= 1:
        raise ValueError("amplitude deve estar no intervalo (0, 1]")
    try:
        rampa = Decimal(str(rampa_ms))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("rampa_ms deve ser um número não negativo") from None
    if not rampa.is_finite() or rampa < 0:
        raise ValueError("rampa_ms deve ser um número não negativo")
    return taxa_amostragem, amplitude, rampa


def _amostra(inicio_ms: Decimal, fim_ms: Decimal, taxa: int) -> tuple[int, int]:
    inicio = int((inicio_ms * taxa) / 1000)
    fim = int((fim_ms * taxa) / 1000)
    return inicio, max(inicio, fim)


def gerar_pcm(
    timeline: Timeline,
    *,
    taxa_amostragem: int = AMOSTRA_PADRAO,
    amplitude: float = AMPLITUDE_PADRAO,
    rampa_ms: float | int | Decimal = RAMPA_MS_PADRAO,
) -> array.array:
    """Devolve os samples PCM de 16 bits como um ``array.array('h')``."""
    if not isinstance(timeline, Timeline):
        raise TypeError("a geração espera uma Timeline")
    taxa, amplitude, rampa = _validar_opcoes(
        taxa_amostragem, amplitude, rampa_ms)

    total = int((timeline.duracao_total_ms * taxa) / 1000)
    amostras = array.array("h", [0]) * total
    if total == 0:
        return amostras

    try:
        frequencia = float(timeline.tom)
    except (TypeError, ValueError, OverflowError):
        raise ErroGeracao(
            f"tom inválido para geração de áudio: {timeline.tom!r}") from None
    if not math.isfinite(frequencia) or frequencia <= 0:
        raise ErroGeracao(
            f"tom inválido para geração de áudio: {timeline.tom!r}")

    rampa_amostras = max(1, int((rampa * taxa) / 1000))
    passo = 2.0 * math.pi * frequencia / taxa
    pico = amplitude * VALOR_MAXIMO

    for evento in timeline.eventos:
        if evento.tipo != "tom":
            continue
        inicio, fim = _amostra(evento.inicio_ms, evento.fim_ms, taxa)
        quantidade = min(fim, total) - inicio
        if quantidade <= 0:
            continue
        transicao = min(rampa_amostras, max(1, quantidade // 3))
        for indice in range(quantidade):
            valor = math.sin(passo * indice)
            if indice < transicao:
                valor *= indice / transicao
            elif indice >= quantidade - transicao:
                valor *= (quantidade - 1 - indice) / transicao
            amostras[inicio + indice] = int(round(valor * pico))

    return amostras


def gerar_wav(
    timeline: Timeline,
    *,
    taxa_amostragem: int = AMOSTRA_PADRAO,
    amplitude: float = AMPLITUDE_PADRAO,
    rampa_ms: float | int | Decimal = RAMPA_MS_PADRAO,
) -> bytes:
    """Devolve um arquivo WAV mono de 16 bits em memória."""
    amostras = gerar_pcm(
        timeline,
        taxa_amostragem=taxa_amostragem,
        amplitude=amplitude,
        rampa_ms=rampa_ms,
    )
    memoria = io.BytesIO()
    with wave.open(memoria, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa_amostragem)
        arquivo.writeframes(amostras.tobytes())
    return memoria.getvalue()


def escrever_wav(
    timeline: Timeline,
    caminho: str | Path,
    **opcoes,
) -> Path:
    """Grava o WAV em ``caminho`` e devolve o caminho usado."""
    destino = Path(caminho)
    destino.write_bytes(gerar_wav(timeline, **opcoes))
    return destino
