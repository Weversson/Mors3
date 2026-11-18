"""Modelo de dados produzido pela análise semântica de MorseLang."""

from dataclasses import dataclass
from decimal import Decimal

from src.ast_morselang import Emissao, Mensagem, Programa


TOM_PADRAO = Decimal("600")
VELOCIDADE_PADRAO = Decimal("20")

TOM_MINIMO = Decimal("100")
TOM_MAXIMO = Decimal("20000")


@dataclass(frozen=True, slots=True)
class ResultadoSemantico:
    """Programa validado, com configurações efetivas e comandos resolvidos.

    `tom` e `velocidade` já incluem os padrões da linguagem. Os valores são
    `Decimal` para preservar exatamente os lexemas numéricos sem depender de
    limites de conversão para inteiros muito grandes.
    """

    programa: Programa
    tom: Decimal
    velocidade: Decimal
    mensagens: tuple[Mensagem, ...]
    emissoes: tuple[Emissao, ...]

    @property
    def tom_hz(self) -> Decimal:
        return self.tom

    @property
    def velocidade_wpm(self) -> Decimal:
        return self.velocidade

    @property
    def quantidade_emissoes(self) -> int:
        return len(self.emissoes)
