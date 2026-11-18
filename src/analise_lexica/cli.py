"""Interface de linha de comando da análise léxica de MorseLang."""

import argparse
import sys
from pathlib import Path

from .analisador import analisar
from .erros import ErroLexico


def main(
    argv: list[str] | None = None,
    *,
    stdout=None,
    stderr=None,
) -> int:
    """Lista os tokens de um arquivo `.mf`.

    Retorna 0 em caso de sucesso, 1 para falha de leitura ou erro léxico e 2
    para uso incorreto da linha de comando. A tabela de tokens vai para stdout;
    os diagnósticos vão para stderr.
    """
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr

    parser = argparse.ArgumentParser(
        prog="lexico",
        description="Lista os tokens de um programa MorseLang, sem executá-lo.",
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
        tokens = analisar(fonte)
    except ErroLexico as erro:
        print(f"erro léxico: {erro}", file=stderr)
        return 1

    for token in tokens:
        print(token.formatar(), file=stdout)
    print(f"{len(tokens)} tokens reconhecidos", file=stdout)
    return 0
