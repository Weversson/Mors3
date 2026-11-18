"""Interface de linha de comando da análise semântica de MorseLang."""

import argparse
import sys
from pathlib import Path

from src.analise_lexica import ErroLexico
from src.sintatico import ErroSintatico, analisar as analisar_sintatico

from .analisador import analisar
from .erros import ErroSemantico


def _numero(valor) -> str:
    return format(valor, "f")


def main(
    argv: list[str] | None = None,
    *,
    stdout=None,
    stderr=None,
) -> int:
    """Valida léxica, sintática e semanticamente um arquivo `.mf`.

    Retorna 0 no sucesso, 1 para falha de leitura ou de alguma análise e 2
    para uso incorreto da linha de comando. Nenhum arquivo de saída é gerado.
    """
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr

    parser = argparse.ArgumentParser(
        prog="semantico",
        description="Valida semanticamente um programa MorseLang, sem executá-lo.",
    )
    parser.add_argument("arquivo", help="caminho do programa .mf")
    args = parser.parse_args(argv)

    try:
        fonte = Path(args.arquivo).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        print(f"erro: não foi possível ler '{args.arquivo}': {erro}",
              file=stderr)
        return 1

    try:
        resultado = analisar(analisar_sintatico(fonte).programa)
    except ErroLexico as erro:
        print(f"erro léxico: {erro}", file=stderr)
        return 1
    except ErroSintatico as erro:
        print(f"erro sintático: {erro}", file=stderr)
        return 1
    except ErroSemantico as erro:
        print(f"erro semântico: {erro}", file=stderr)
        return 1

    print(
        f"Programa semanticamente válido: "
        f"{len(resultado.emissoes)} emissão(ões); "
        f"tom {_numero(resultado.tom)} Hz; "
        f"velocidade {_numero(resultado.velocidade)} WPM.",
        file=stdout,
    )
    return 0
