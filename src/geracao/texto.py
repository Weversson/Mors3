"""Serialização da timeline em texto Morse legível.

Cada emissão ocupa uma linha. Dentro da linha, caracteres são separados por um
espaço e palavras por `` / ``. A barra não é um símbolo Morse: ela apenas
representa o intervalo de palavra, que na timeline dura sete unidades.
"""

from pathlib import Path

from src.execucao import Timeline
from src.morse_tables import morse_for

from .erros import ErroGeracao

SEPARADOR_CARACTERES = " "
SEPARADOR_PALAVRAS = " / "
SEPARADOR_EMISSOES = "\n"


def morse_de_texto(texto: str) -> str:
    """Converte um texto já normalizado em sua representação textual Morse."""
    if not isinstance(texto, str):
        raise TypeError("o texto deve ser str")
    palavras = []
    for palavra in texto.split():
        codigos = []
        for caractere in palavra:
            codigo = morse_for(caractere)
            if codigo is None:
                raise ErroGeracao(
                    f"o caractere {caractere!r} não possui representação Morse")
            codigos.append(codigo)
        palavras.append(SEPARADOR_CARACTERES.join(codigos))
    return SEPARADOR_PALAVRAS.join(palavras)


def gerar_morse(timeline: Timeline) -> str:
    """Devolve o conteúdo completo de um arquivo ``.morse``."""
    if not isinstance(timeline, Timeline):
        raise TypeError("a geração espera uma Timeline")
    linhas = (morse_de_texto(texto) for texto in timeline.textos)
    return SEPARADOR_EMISSOES.join(linhas) + SEPARADOR_EMISSOES


def escrever_morse(timeline: Timeline, caminho: str | Path) -> Path:
    """Grava o texto Morse em ``caminho`` e devolve o caminho usado."""
    destino = Path(caminho)
    destino.write_text(gerar_morse(timeline), encoding="utf-8")
    return destino
