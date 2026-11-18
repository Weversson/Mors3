"""Modelo de dados produzido pela análise léxica de MorseLang."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenInfo:
    """Um token reconhecido, com posição contada a partir de 1.

    O texto preserva o lexema original, inclusive as aspas dos literais de
    texto. `tipo` corresponde ao nome simbólico definido na gramática ANTLR.
    """

    tipo: str
    texto: str
    linha: int
    coluna: int

    def formatar(self) -> str:
        """Representação usada pela CLI, com o lexema entre aspas simples."""
        return (f"{self.tipo} {self.texto!r} "
                f"linha {self.linha} coluna {self.coluna}")
