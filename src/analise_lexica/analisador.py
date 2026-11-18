"""Análise léxica de MorseLang sobre o lexer gerado pelo ANTLR."""

from collections.abc import Iterator

from antlr4 import InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from gerado.MorseLang import MorseLang

from .erros import ErroLexico
from .modelo import TokenInfo


class _FalhaNoPrimeiroErro(ErrorListener):
    """Converte o primeiro erro do ANTLR em `ErroLexico` com posição 1-based."""

    _PREFIXO_ANTLR = "token recognition error at: "

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # O ANTLR já entrega o trecho ofensor entre aspas e com escapes, o que
        # mantém o diagnóstico em uma única linha mesmo para quebra de linha.
        trecho = msg.removeprefix(self._PREFIXO_ANTLR)
        raise ErroLexico(line, column + 1,
                         f"trecho não reconhecido: {trecho}")


def criar_lexer(texto: str) -> MorseLang:
    """Cria o lexer ANTLR configurado para interromper no primeiro erro.

    A função é reutilizada pelo analisador sintático para garantir que a fonte
    inteira tenha tokens válidos antes do parser. O lexer devolvido ainda não
    foi consumido.
    """
    if not isinstance(texto, str):
        raise TypeError("o texto da análise léxica deve ser str")

    lexer = MorseLang(InputStream(texto))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_FalhaNoPrimeiroErro())
    return lexer


def iterar_tokens(texto: str) -> Iterator[TokenInfo]:
    """Gera os tokens de `texto` na ordem da fonte, sem EOF.

    Comentários e espaços são descartados pela gramática e, por isso, não
    aparecem no resultado. Um erro léxico interrompe a iteração.
    """
    lexer = criar_lexer(texto)
    while True:
        token = lexer.nextToken()
        if token.type == Token.EOF:
            return
        yield TokenInfo(
            tipo=lexer.symbolicNames[token.type],
            texto=token.text,
            linha=token.line,
            coluna=token.column + 1,
        )


def analisar(texto: str) -> list[TokenInfo]:
    """Analisa `texto` por completo e devolve a lista de tokens reconhecidos."""
    return list(iterar_tokens(texto))
