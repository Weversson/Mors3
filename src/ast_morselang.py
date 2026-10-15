"""Árvore sintática abstrata de MorseLang, independente do protótipo de texto livre."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class No:
    linha: int
    coluna: int


@dataclass(frozen=True)
class Texto(No):
    valor: str


@dataclass(frozen=True)
class Referencia(No):
    nome: str


@dataclass(frozen=True)
class Numero(No):
    # Preserva a escrita original. Conversão, limites e positividade são da E4.
    lexema: str


@dataclass(frozen=True)
class Concatenacao(No):
    esquerda: Expressao
    direita: Expressao


@dataclass(frozen=True)
class Repeticao(No):
    texto: Expressao
    quantidade: Numero


Expressao = Texto | Referencia | Concatenacao | Repeticao


@dataclass(frozen=True)
class Mensagem(No):
    nome: str
    expressao: Expressao


@dataclass(frozen=True)
class Tom(No):
    valor: Numero


@dataclass(frozen=True)
class Velocidade(No):
    valor: Numero


@dataclass(frozen=True)
class Emissao(No):
    expressao: Expressao


Comando = Mensagem | Tom | Velocidade | Emissao


@dataclass(frozen=True)
class Programa(No):
    comandos: tuple[Comando, ...]


def para_dict(no: No) -> dict:
    """Representa a AST em JSON, incluindo tipos dos nós e posições na fonte."""
    resultado = {"tipo": type(no).__name__}
    for campo in fields(no):
        valor = getattr(no, campo.name)
        if isinstance(valor, No):
            valor = para_dict(valor)
        elif isinstance(valor, tuple):
            valor = [para_dict(item) for item in valor]
        resultado[campo.name] = valor
    return resultado
