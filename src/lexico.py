"""Lista os tokens da linguagem Morse da entrega E2."""

import os
import sys

if __name__ == "__main__":
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import argparse
from dataclasses import dataclass
from pathlib import Path

from antlr4 import InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from gerado.MorseLang import MorseLang  # noqa: E402


@dataclass(frozen=True)
class TokenInfo:
    tipo: str
    texto: str
    linha: int
    coluna: int


class ErroLexico(Exception):
    def __init__(self, linha: int, coluna: int, detalhe: str) -> None:
        self.linha = linha
        self.coluna = coluna
        self.detalhe = detalhe
        super().__init__(f"linha {linha}, coluna {coluna}: {detalhe}")


class _FalhaNoPrimeiroErro(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise ErroLexico(line, column + 1, msg)


def analisar(texto: str) -> list[TokenInfo]:
    lexer = MorseLang(InputStream(texto))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_FalhaNoPrimeiroErro())

    resultado = []
    while True:
        token = lexer.nextToken()
        if token.type == Token.EOF:
            return resultado
        resultado.append(TokenInfo(
            tipo=lexer.symbolicNames[token.type],
            texto=token.text,
            linha=token.line,
            coluna=token.column + 1,
        ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lista os tokens de um programa Morse.")
    parser.add_argument("arquivo", help="caminho do programa .mf")
    args = parser.parse_args(argv)

    try:
        fonte = Path(args.arquivo).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        print(f"erro: não foi possível ler '{args.arquivo}': {erro}", file=sys.stderr)
        return 1

    try:
        tokens = analisar(fonte)
    except ErroLexico as erro:
        print(f"erro léxico: {erro}", file=sys.stderr)
        return 1

    for token in tokens:
        print(f"{token.tipo} {token.texto!r} linha {token.linha} coluna {token.coluna}")
    print(f"{len(tokens)} tokens reconhecidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
