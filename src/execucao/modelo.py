"""Modelo de dados da execução de MorseLang.

A execução não gera arquivos: ela transforma as emissões já validadas em uma
linha do tempo de tons e silêncios. A mesma timeline alimenta a visualização e
o áudio, garantindo que os dois permaneçam sincronizados.
"""

from dataclasses import dataclass
from decimal import Decimal

# Um ponto dura 1200 / WPM milissegundos (padrão PARIS).
UNIDADE_BASE_MS = Decimal("1200")

TIPOS_EVENTO = frozenset({"tom", "silencio"})
MOTIVOS_SILENCIO = frozenset({"simbolo", "caractere", "palavra", "emissao"})


def texto_decimal(valor: Decimal) -> str:
    """Formata um Decimal sem notação científica, para uso em JSON."""
    return format(valor, "f")


@dataclass(frozen=True, slots=True)
class Evento:
    """Um tom ou silêncio da linha do tempo.

    `inicio_ms` e `duracao_ms` são contínuos: o fim de um evento é o início do
    próximo. `motivo` distingue os silêncios e `emissao` identifica a qual
    comando `emitir` o evento pertence (a partir de 0).
    """

    tipo: str
    inicio_ms: Decimal
    duracao_ms: Decimal
    simbolo: str | None = None
    motivo: str | None = None
    emissao: int | None = None
    caractere: str | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_EVENTO:
            raise ValueError(f"tipo de evento desconhecido: {self.tipo!r}")
        if self.motivo is not None and self.motivo not in MOTIVOS_SILENCIO:
            raise ValueError(f"motivo de silêncio desconhecido: {self.motivo!r}")
        if self.inicio_ms < 0:
            raise ValueError("inicio_ms não pode ser negativo")
        if self.duracao_ms < 0:
            raise ValueError("duracao_ms não pode ser negativa")
        if self.tipo == "tom" and self.simbolo not in {".", "-"}:
            raise ValueError("um tom precisa ter simbolo '.' ou '-'")
        if self.tipo == "silencio" and self.simbolo is not None:
            raise ValueError("um silêncio não pode ter simbolo")

    @property
    def fim_ms(self) -> Decimal:
        return self.inicio_ms + self.duracao_ms

    def para_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "inicio_ms": texto_decimal(self.inicio_ms),
            "duracao_ms": texto_decimal(self.duracao_ms),
            "fim_ms": texto_decimal(self.fim_ms),
            "simbolo": self.simbolo,
            "motivo": self.motivo,
            "emissao": self.emissao,
            "caractere": self.caractere,
        }


@dataclass(frozen=True, slots=True)
class Timeline:
    """Programa expandido em eventos de tom e silêncio."""

    tom: Decimal
    velocidade: Decimal
    unidade_ms: Decimal
    textos: tuple[str, ...]
    texto: str
    eventos: tuple[Evento, ...]

    @property
    def duracao_total_ms(self) -> Decimal:
        return self.eventos[-1].fim_ms if self.eventos else Decimal(0)

    @property
    def quantidade_eventos(self) -> int:
        return len(self.eventos)

    @property
    def quantidade_emissoes(self) -> int:
        return len(self.textos)

    def para_dict(self) -> dict:
        return {
            "tom": texto_decimal(self.tom),
            "velocidade": texto_decimal(self.velocidade),
            "unidade_ms": texto_decimal(self.unidade_ms),
            "texto": self.texto,
            "textos": list(self.textos),
            "duracao_total_ms": texto_decimal(self.duracao_total_ms),
            "quantidade_eventos": self.quantidade_eventos,
            "quantidade_emissoes": self.quantidade_emissoes,
            "eventos": [evento.para_dict() for evento in self.eventos],
        }
