"""Expansão de um programa MorseLang validado em uma linha do tempo.

As regras de duração seguem o padrão PARIS: um ponto dura ``1200 / WPM``
milissegundos, um traço dura três pontos, o silêncio entre símbolos dura um
ponto, entre caracteres três pontos e entre palavras sete pontos. Emissões
distintas são separadas por um espaço, como define a linguagem.
"""

from decimal import Decimal, InvalidOperation

from src.analise_semantica.modelo import ResultadoSemantico
from src.ast_morselang import (
    Concatenacao, Expressao, Mensagem, Referencia, Repeticao, Texto,
)
from src.morse_tables import morse_for

from .erros import ErroExecucao
from .modelo import UNIDADE_BASE_MS, Evento, Timeline


def unidade_ms(velocidade: Decimal) -> Decimal:
    """Duração de um ponto em milissegundos para a velocidade informada."""
    if not isinstance(velocidade, Decimal):
        try:
            velocidade = Decimal(velocidade)
        except (InvalidOperation, TypeError, ValueError):
            raise ErroExecucao(
                f"velocidade inválida: {velocidade!r}") from None
    if velocidade <= 0:
        raise ErroExecucao("a velocidade deve ser um inteiro positivo")
    return UNIDADE_BASE_MS / velocidade


def _limitar(texto: str, limite: int | None) -> str:
    if limite is not None and len(texto) > limite:
        raise ErroExecucao(
            f"a expansão excede o limite de {limite} caracteres")
    return texto


def _quantidade(expressao: Repeticao) -> int:
    try:
        return int(expressao.quantidade.lexema)
    except (TypeError, ValueError):
        raise ErroExecucao(
            "a quantidade de repetição deve ser um inteiro positivo; "
            f"recebido: {expressao.quantidade.lexema!r}") from None


def _expandir_expressao(
    expressao: Expressao,
    simbolos: dict[str, Mensagem],
    cache: dict[str, str],
    limite: int | None,
) -> str:
    if isinstance(expressao, Texto):
        return _limitar(expressao.valor, limite)

    if isinstance(expressao, Referencia):
        if expressao.nome in cache:
            return cache[expressao.nome]
        mensagem = simbolos.get(expressao.nome)
        if mensagem is None:
            raise ErroExecucao(
                f"nome {expressao.nome!r} não foi declarado")
        valor = _expandir_expressao(mensagem.expressao, simbolos, cache, limite)
        cache[expressao.nome] = valor
        return valor

    if isinstance(expressao, Concatenacao):
        esquerda = _expandir_expressao(
            expressao.esquerda, simbolos, cache, limite)
        direita = _expandir_expressao(
            expressao.direita, simbolos, cache, limite)
        return _limitar(esquerda + direita, limite)

    if isinstance(expressao, Repeticao):
        texto = _expandir_expressao(expressao.texto, simbolos, cache, limite)
        quantidade = _quantidade(expressao)
        if quantidade <= 0:
            raise ErroExecucao(
                "a quantidade de repetição deve ser um inteiro positivo; "
                f"recebido: {expressao.quantidade.lexema}")
        if limite is not None and len(texto) * quantidade > limite:
            raise ErroExecucao(
                f"a expansão excede o limite de {limite} caracteres")
        return texto * quantidade

    raise TypeError(f"expressão desconhecida: {type(expressao).__name__}")


def expandir_texto(
    expressao: Expressao,
    mensagens: tuple[Mensagem, ...] = (),
    *,
    limite_caracteres: int | None = None,
) -> str:
    """Expande uma expressão, resolvendo referências às mensagens informadas."""
    simbolos = {mensagem.nome: mensagem for mensagem in mensagens}
    return _expandir_expressao(
        expressao, simbolos, {}, limite_caracteres)


def _normalizar(texto: str) -> str:
    """Colapsa espaços em branco em separadores de palavra."""
    return " ".join(texto.split())


def _montar_eventos(
    textos: tuple[str, ...], unidade: Decimal) -> tuple[Evento, ...]:
    eventos: list[Evento] = []
    inicio = Decimal(0)

    def adicionar(
        tipo: str,
        duracao: Decimal,
        *,
        emissao: int,
        simbolo: str | None = None,
        motivo: str | None = None,
        caractere: str | None = None,
    ) -> None:
        nonlocal inicio
        eventos.append(Evento(
            tipo=tipo,
            inicio_ms=inicio,
            duracao_ms=duracao,
            simbolo=simbolo,
            motivo=motivo,
            emissao=emissao,
            caractere=caractere,
        ))
        inicio += duracao

    for indice_emissao, texto in enumerate(textos):
        for indice_palavra, palavra in enumerate(texto.split()):
            for indice_caractere, caractere in enumerate(palavra):
                codigo = morse_for(caractere)
                if codigo is None:
                    raise ErroExecucao(
                        f"o caractere {caractere!r} não possui "
                        "representação em Morse")

                if eventos:
                    if indice_caractere == 0:
                        if indice_palavra == 0 and indice_emissao > 0:
                            motivo = "emissao"
                        else:
                            motivo = "palavra"
                        adicionar(
                            "silencio", 7 * unidade,
                            emissao=indice_emissao, motivo=motivo)
                    else:
                        adicionar(
                            "silencio", 3 * unidade,
                            emissao=indice_emissao, motivo="caractere")

                for indice_simbolo, simbolo in enumerate(codigo):
                    if indice_simbolo > 0:
                        adicionar(
                            "silencio", unidade,
                            emissao=indice_emissao, motivo="simbolo",
                            caractere=caractere)
                    duracao = unidade if simbolo == "." else 3 * unidade
                    adicionar(
                        "tom", duracao,
                        emissao=indice_emissao, simbolo=simbolo,
                        caractere=caractere)

    return tuple(eventos)


def expandir(
    resultado: ResultadoSemantico,
    *,
    limite_caracteres: int | None = None,
) -> Timeline:
    """Expande as emissões validadas em uma timeline de tons e silêncios.

    ``limite_caracteres`` é uma proteção opcional para interfaces interativas;
    por padrão não há limite, preservando a especificação da linguagem.
    """
    if not isinstance(resultado, ResultadoSemantico):
        raise TypeError("a execução espera um ResultadoSemantico")

    unidade = unidade_ms(resultado.velocidade)
    simbolos = {mensagem.nome: mensagem for mensagem in resultado.mensagens}
    cache: dict[str, str] = {}
    textos = tuple(
        _normalizar(_expandir_expressao(
            emissao.expressao, simbolos, cache, limite_caracteres))
        for emissao in resultado.emissoes
    )
    eventos = _montar_eventos(textos, unidade)
    texto = " ".join(parte for parte in textos if parte)
    return Timeline(
        tom=resultado.tom,
        velocidade=resultado.velocidade,
        unidade_ms=unidade,
        textos=textos,
        texto=texto,
        eventos=eventos,
    )
