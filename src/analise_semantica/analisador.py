"""Análise semântica de MorseLang sobre a AST produzida pelo parser."""

from decimal import Decimal, InvalidOperation

from src.ast_morselang import (
    Comando, Concatenacao, Emissao, Expressao, Mensagem, Numero, Programa,
    Referencia, Repeticao, Texto, Tom, Velocidade,
)
from src.morse_tables import morse_for

from .erros import ErroSemantico
from .modelo import (
    TOM_MAXIMO, TOM_MINIMO, TOM_PADRAO, VELOCIDADE_PADRAO, ResultadoSemantico,
)


def _decimal(numero: Numero) -> Decimal:
    try:
        return Decimal(numero.lexema)
    except InvalidOperation:
        # O lexer só produz sequências de dígitos; esta proteção cobre uma AST
        # construída manualmente ou um lexema alterado fora do fluxo normal.
        raise ErroSemantico(
            numero.linha, numero.coluna,
            f"número inválido: {numero.lexema!r}",
        ) from None


def _inteiro_positivo(lexema: str) -> bool:
    """Confere positividade sem converter lexemas com milhares de dígitos."""
    return lexema.strip("0") != ""


def _descrever_numero(lexema: str) -> str:
    if len(lexema) <= 40:
        return lexema
    return f"{lexema[:37]}..."


class AnalisadorSemantico:
    """Valida uma AST e reúne as informações efetivas do programa.

    A análise interrompe no primeiro erro, como as etapas léxica e sintática.
    A tabela de símbolos é global e guarda as mensagens na ordem de declaração.
    """

    def __init__(self) -> None:
        self._reiniciar()

    def _reiniciar(self) -> None:
        self._simbolos: dict[str, Mensagem] = {}
        self._mensagens: list[Mensagem] = []
        self._emissoes: list[Emissao] = []
        self._tom = TOM_PADRAO
        self._velocidade = VELOCIDADE_PADRAO

    def analisar(self, programa: Programa) -> ResultadoSemantico:
        if not isinstance(programa, Programa):
            raise TypeError("a análise semântica espera um Programa")

        self._reiniciar()
        for comando in programa.comandos:
            self._visitar_comando(comando)

        return ResultadoSemantico(
            programa=programa,
            tom=self._tom,
            velocidade=self._velocidade,
            mensagens=tuple(self._mensagens),
            emissoes=tuple(self._emissoes),
        )

    def _visitar_comando(self, comando: Comando) -> None:
        if isinstance(comando, Mensagem):
            self._visitar_mensagem(comando)
        elif isinstance(comando, Tom):
            self._visitar_tom(comando)
        elif isinstance(comando, Velocidade):
            self._visitar_velocidade(comando)
        elif isinstance(comando, Emissao):
            self._visitar_emissao(comando)
        else:
            raise TypeError(f"comando desconhecido: {type(comando).__name__}")

    def _visitar_mensagem(self, mensagem: Mensagem) -> None:
        if mensagem.nome in self._simbolos:
            raise ErroSemantico(
                mensagem.linha, mensagem.coluna,
                f"nome {mensagem.nome!r} já foi declarado",
            )

        self._validar_expressao(mensagem.expressao)
        self._simbolos[mensagem.nome] = mensagem
        self._mensagens.append(mensagem)

    def _visitar_tom(self, comando: Tom) -> None:
        valor = _decimal(comando.valor)
        if not TOM_MINIMO <= valor <= TOM_MAXIMO:
            raise ErroSemantico(
                comando.valor.linha, comando.valor.coluna,
                "o tom deve estar entre 100 e 20000 Hz; "
                f"recebido: {comando.valor.lexema}",
            )
        self._tom = valor

    def _visitar_velocidade(self, comando: Velocidade) -> None:
        if not _inteiro_positivo(comando.valor.lexema):
            raise ErroSemantico(
                comando.valor.linha, comando.valor.coluna,
                "a velocidade deve ser um inteiro positivo; "
                f"recebido: {_descrever_numero(comando.valor.lexema)}",
            )
        self._velocidade = _decimal(comando.valor)

    def _visitar_emissao(self, emissao: Emissao) -> None:
        self._validar_expressao(emissao.expressao)
        self._emissoes.append(emissao)

    def _validar_expressao(self, expressao: Expressao) -> None:
        if isinstance(expressao, Texto):
            self._validar_texto(expressao)
        elif isinstance(expressao, Referencia):
            if expressao.nome not in self._simbolos:
                raise ErroSemantico(
                    expressao.linha, expressao.coluna,
                    f"nome {expressao.nome!r} não foi declarado",
                )
        elif isinstance(expressao, Concatenacao):
            self._validar_expressao(expressao.esquerda)
            self._validar_expressao(expressao.direita)
        elif isinstance(expressao, Repeticao):
            self._validar_expressao(expressao.texto)
            if not _inteiro_positivo(expressao.quantidade.lexema):
                raise ErroSemantico(
                    expressao.quantidade.linha, expressao.quantidade.coluna,
                    "a quantidade de repetição deve ser um inteiro positivo; "
                    f"recebido: {_descrever_numero(expressao.quantidade.lexema)}",
                )
        else:
            raise TypeError(
                f"expressão desconhecida: {type(expressao).__name__}")

    def _validar_texto(self, texto: Texto) -> None:
        for deslocamento, caractere in enumerate(texto.valor):
            # Espaços separam palavras e não recebem código Morse.
            if caractere.isspace() or morse_for(caractere) is not None:
                continue
            raise ErroSemantico(
                texto.linha, texto.coluna + 1 + deslocamento,
                f"o caractere {caractere!r} não possui representação em Morse",
            )


def analisar(programa: Programa) -> ResultadoSemantico:
    """Valida a AST completa e devolve as configurações efetivas do programa."""
    return AnalisadorSemantico().analisar(programa)


def analisar_fonte(fonte: str) -> ResultadoSemantico:
    """Executa as etapas léxica, sintática e semântica sobre o texto fonte."""
    from src.sintatico import analisar as analisar_sintatico

    return analisar(analisar_sintatico(fonte).programa)
