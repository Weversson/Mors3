"""CLI da execução headless: imprime a timeline de um programa MorseLang."""

import argparse
import json
from pathlib import Path
import sys

from src.analise_lexica import ErroLexico
from src.semantico import ErroSemantico, analisar_fonte
from src.sintatico import ErroSintatico

from .erros import ErroExecucao
from .expansor import expandir
from .modelo import texto_decimal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="execucao",
        description=(
            "Valida um programa MorseLang e imprime a timeline de tons e "
            "silêncios, sem gerar arquivos."
        ),
    )
    parser.add_argument("arquivo", help="caminho do programa .mf")
    parser.add_argument(
        "--limite", type=int, default=None,
        help="limite opcional de caracteres expandidos",
    )
    parser.add_argument(
        "--resumo", action="store_true",
        help="imprime um resumo legível em vez do JSON completo",
    )
    args = parser.parse_args(argv)
    if args.limite is not None and args.limite < 0:
        parser.error("--limite deve ser não negativo")

    try:
        fonte = Path(args.arquivo).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        print(f"erro: não foi possível ler '{args.arquivo}': {erro}",
              file=sys.stderr)
        return 1

    try:
        timeline = expandir(
            analisar_fonte(fonte), limite_caracteres=args.limite)
    except ErroLexico as erro:
        print(f"erro léxico: {erro}", file=sys.stderr)
        return 1
    except ErroSintatico as erro:
        print(f"erro sintático: {erro}", file=sys.stderr)
        return 1
    except ErroSemantico as erro:
        print(f"erro semântico: {erro}", file=sys.stderr)
        return 1
    except ErroExecucao as erro:
        print(f"erro de execução: {erro}", file=sys.stderr)
        return 1

    if args.resumo:
        texto = timeline.texto if timeline.texto else "<vazio>"
        print(
            f"{timeline.quantidade_emissoes} emissão(ões); "
            f"tom {texto_decimal(timeline.tom)} Hz; "
            f"velocidade {texto_decimal(timeline.velocidade)} WPM; "
            f"{timeline.quantidade_eventos} evento(s); "
            f"{texto_decimal(timeline.duracao_total_ms)} ms"
        )
        print(texto)
        return 0

    print(json.dumps(timeline.para_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
