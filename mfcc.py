#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.build_ast import parse_source  # noqa: E402
from src.codegen import emit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="mfcc",
        description="Compila um arquivo de texto (.mf) para código Morse.",
        epilog="Ex: .venv/bin/python mfcc.py examples/olamundo.mf --wpm 20",
    )
    ap.add_argument("input", help="arquivo de texto fonte (.mf)")
    ap.add_argument("-o", "--output", metavar="BASE",
                    help="caminho base de saída (sem extensão)")
    ap.add_argument("--freq", type=int, default=600,
                    help="frequência do tom em Hz (padrão: 600)")
    ap.add_argument("--wpm", type=int, default=20,
                    help="velocidade em palavras/minuto (padrão: 20)")
    args = ap.parse_args()

    if not 100 <= args.freq <= 20000:
        ap.error("--freq deve estar entre 100 e 20000")
    if args.wpm <= 0:
        ap.error("--wpm deve ser um inteiro positivo")

    try:
        source = Path(args.input).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"erro: não foi possível ler '{args.input}': {e}", file=sys.stderr)
        return 1

    doc, warnings = parse_source(source)
    if warnings:
        print(f"aviso: {warnings} caractere(s) sem código Morse foram ignorados",
              file=sys.stderr)

    if not doc.words:
        print("erro: nenhum texto compilável encontrado", file=sys.stderr)
        return 1

    base = args.output or str(Path(args.input).with_suffix(""))
    try:
        morse_path, wav_path = emit(doc, base, args.freq, args.wpm)
    except OSError as e:
        print(f"erro: falha ao gerar os arquivos de saída: {e}", file=sys.stderr)
        return 1

    print(f"OK: gerado {morse_path} (texto) e {wav_path} (áudio)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
