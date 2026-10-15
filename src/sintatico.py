"""Análise sintática de MorseLang: fonte -> árvore ANTLR e AST, sem execução."""

import os
import sys

if __name__ == "__main__":
    # Impede que src/ast.py oculte ast da biblioteca padrão na execução direta.
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from antlr4 import CommonTokenStream, Token
from antlr4.error.ErrorListener import ErrorListener

from gerado.MorseLangParser import MorseLangParser
from src.ast_morselang import Programa, para_dict
from src.construir_ast import ConstruirAST
from src.lexico import ErroLexico, criar_lexer


class ErroSintatico(Exception):
    def __init__(self, linha: int, coluna: int, detalhe: str) -> None:
        self.linha = linha
        self.coluna = coluna
        self.detalhe = detalhe
        super().__init__(f"linha {linha}, coluna {coluna}: {detalhe}")


def _nome_token(parser, tipo: int) -> str:
    if tipo == Token.EOF:
        return "fim do arquivo"
    if 0 <= tipo < len(parser.literalNames):
        literal = parser.literalNames[tipo]
        if literal != "<INVALID>":
            return literal
    nomes = {"IDENT": "identificador", "TEXTO": "texto entre aspas",
             "INTEIRO": "inteiro", "REAL": "número real"}
    simbolo = parser.symbolicNames[tipo]
    return nomes.get(simbolo, simbolo)


class _FalhaSintatica(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        encontrado = ("fim do arquivo" if offendingSymbol.type == Token.EOF
                      else repr(offendingSymbol.text))
        esperados = ", ".join(_nome_token(recognizer, tipo)
                              for tipo in recognizer.getExpectedTokens())
        raise ErroSintatico(line, column + 1,
                            f"encontrado {encontrado}; esperado: {esperados}")


@dataclass(frozen=True)
class ResultadoAnalise:
    programa: Programa
    arvore: str


def analisar(texto: str) -> ResultadoAnalise:
    """Analisa toda a fonte; falhas léxicas ou sintáticas não produzem uma AST."""
    tokens = CommonTokenStream(criar_lexer(texto))
    # Valida também os caracteres no final da fonte antes de iniciar o parser.
    tokens.fill()
    tokens.seek(0)
    parser = MorseLangParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(_FalhaSintatica())
    arvore = parser.programa()
    return ResultadoAnalise(programa=ConstruirAST().visit(arvore),
                            arvore=arvore.toStringTree(recog=parser))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analisa a sintaxe de um programa MorseLang, sem executá-lo."
    )
    parser.add_argument("arquivo", help="caminho do programa .mf")
    saida = parser.add_mutually_exclusive_group()
    saida.add_argument("--arvore", action="store_true",
                       help="mostra a árvore sintática concreta do ANTLR")
    saida.add_argument("--ast", action="store_true",
                       help="mostra a árvore sintática abstrata em JSON")
    args = parser.parse_args(argv)

    try:
        fonte = Path(args.arquivo).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erro:
        print(f"erro: não foi possível ler '{args.arquivo}': {erro}", file=sys.stderr)
        return 1

    try:
        resultado = analisar(fonte)
    except ErroLexico as erro:
        print(f"erro léxico: {erro}", file=sys.stderr)
        return 1
    except ErroSintatico as erro:
        print(f"erro sintático: {erro}", file=sys.stderr)
        return 1

    if args.ast:
        print(json.dumps(para_dict(resultado.programa), ensure_ascii=False, indent=2))
    elif args.arvore:
        print(resultado.arvore)
    else:
        print(f"Programa sintaticamente válido: {len(resultado.programa.comandos)} comando(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
