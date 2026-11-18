"""CLI da geração de arquivos ``.morse`` e ``.wav``."""

import argparse
from pathlib import Path
import sys

from src.analise_lexica import ErroLexico
from src.analise_semantica import ErroSemantico
from src.execucao import ErroExecucao, expandir
from src.sintatico import ErroSintatico
from src.semantico import analisar_fonte

from . import AMOSTRA_PADRAO, escrever_morse, escrever_wav


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="geracao",
        description=(
            "Gera .morse e .wav a partir de um programa MorseLang validado."
        ),
    )
    parser.add_argument("entrada", help="arquivo .mf de entrada")
    parser.add_argument("--morse", metavar="CAMINHO",
                        help="caminho do arquivo .morse")
    parser.add_argument("--wav", metavar="CAMINHO",
                        help="caminho do arquivo .wav")
    parser.add_argument("--limite", type=int,
                        help="limite de caracteres expandidos")
    parser.add_argument("--taxa", type=int, default=AMOSTRA_PADRAO,
                        help=f"taxa de amostragem do WAV (padrão: {AMOSTRA_PADRAO})")
    args = parser.parse_args(argv)

    if args.limite is not None and args.limite < 0:
        parser.error("--limite deve ser não negativo")
    if args.taxa <= 0:
        parser.error("--taxa deve ser positiva")

    caminho_entrada = Path(args.entrada)
    try:
        fonte = caminho_entrada.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        print(f"erro: não foi possível ler '{args.entrada}': {erro}",
              file=sys.stderr)
        return 1

    try:
        resultado = analisar_fonte(fonte)
        timeline = expandir(resultado, limite_caracteres=args.limite)
    except (ErroLexico, ErroSintatico, ErroSemantico, ErroExecucao) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    if args.morse is None and args.wav is None:
        quer_morse = quer_wav = True
    else:
        quer_morse = args.morse is not None
        quer_wav = args.wav is not None

    base = caminho_entrada.with_suffix("")
    destino_morse = Path(args.morse) if args.morse else base.with_suffix(".morse")
    destino_wav = Path(args.wav) if args.wav else base.with_suffix(".wav")

    criados = []
    try:
        if quer_morse:
            criados.append(escrever_morse(timeline, destino_morse))
        if quer_wav:
            criados.append(escrever_wav(
                timeline, destino_wav, taxa_amostragem=args.taxa))
    except OSError as erro:
        print(f"erro: falha ao gravar a saída: {erro}", file=sys.stderr)
        return 1

    for caminho in criados:
        print(f"gerado {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
