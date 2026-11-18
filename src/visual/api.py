"""API JSON da visualização de MorseLang.

A API executa a cadeia completa e devolve um dicionário pronto para JSON. Erros
de análise não são falhas HTTP: eles voltam com ``ok: false`` e a etapa que os
produziu, para que a interface possa mostrar tokens e AST parciais.
"""

from src.analise_lexica import ErroLexico, iterar_tokens
from src.analise_semantica import ErroSemantico
from src.analise_semantica import analisar as analisar_semantico
from src.ast_morselang import para_dict
from src.execucao import ErroExecucao, Timeline, expandir, texto_decimal
from src.sintatico import ErroSintatico
from src.sintatico import analisar as analisar_sintatico

LIMITE_PADRAO = 10_000


def _token_para_dict(token) -> dict:
    return {
        "tipo": token.tipo,
        "texto": token.texto,
        "linha": token.linha,
        "coluna": token.coluna,
    }


def _simbolo_para_dict(mensagem) -> dict:
    return {
        "nome": mensagem.nome,
        "linha": mensagem.linha,
        "coluna": mensagem.coluna,
    }


def _resposta_erro(
    etapa: str,
    erro: Exception,
    *,
    tokens: list[dict],
    ast: dict | None = None,
) -> dict:
    return {
        "ok": False,
        "etapa": etapa,
        "linha": getattr(erro, "linha", None),
        "coluna": getattr(erro, "coluna", None),
        "detalhe": getattr(erro, "detalhe", str(erro)),
        "tokens": tokens,
        "ast": ast,
    }


def _validar_limite(limite: int | None) -> None:
    if limite is None:
        return
    if isinstance(limite, bool) or not isinstance(limite, int) or limite < 0:
        raise ValueError("limite_caracteres deve ser um inteiro não negativo")


def _pipeline(
    fonte: str,
    limite_caracteres: int | None,
) -> tuple[dict | None, dict | None]:
    """Executa as quatro etapas e devolve os dados internos ou um erro JSON."""
    tokens: list[dict] = []
    try:
        for token in iterar_tokens(fonte):
            tokens.append(_token_para_dict(token))
    except ErroLexico as erro:
        return None, _resposta_erro("lexico", erro, tokens=tokens)

    try:
        sintatico = analisar_sintatico(fonte)
    except ErroLexico as erro:
        return None, _resposta_erro("lexico", erro, tokens=tokens)
    except ErroSintatico as erro:
        return None, _resposta_erro("sintatico", erro, tokens=tokens)

    ast = para_dict(sintatico.programa)

    try:
        resultado = analisar_semantico(sintatico.programa)
    except ErroSemantico as erro:
        return None, _resposta_erro("semantico", erro, tokens=tokens, ast=ast)

    try:
        timeline = expandir(resultado, limite_caracteres=limite_caracteres)
    except ErroExecucao as erro:
        return None, _resposta_erro("execucao", erro, tokens=tokens, ast=ast)

    return {
        "tokens": tokens,
        "ast": ast,
        "simbolos": [
            _simbolo_para_dict(mensagem)
            for mensagem in resultado.mensagens
        ],
        "timeline": timeline,
    }, None


def analisar_timeline(
    fonte: str,
    *,
    limite_caracteres: int | None = LIMITE_PADRAO,
) -> tuple[Timeline | None, dict | None]:
    """Executa o pipeline e devolve ``(timeline, None)`` ou ``(None, erro)``.

    A forma de tupla permite que a exportação reutilize exatamente as mesmas
    etapas da visualização, inclusive os limites e os erros parciais.
    """
    if not isinstance(fonte, str):
        raise TypeError("a fonte deve ser str")
    _validar_limite(limite_caracteres)

    dados, erro = _pipeline(fonte, limite_caracteres)
    if erro is not None:
        return None, erro
    assert dados is not None
    return dados["timeline"], None


def analisar(fonte: str, *, limite_caracteres: int | None = LIMITE_PADRAO) -> dict:
    """Executa léxica, sintática, semântica e execução sobre ``fonte``.

    ``limite_caracteres`` protege a interface contra expansões muito grandes.
    Use ``None`` para não impor limite, como na API headless.
    """
    if not isinstance(fonte, str):
        raise TypeError("a fonte deve ser str")
    _validar_limite(limite_caracteres)

    dados, erro = _pipeline(fonte, limite_caracteres)
    if erro is not None:
        return erro
    assert dados is not None

    timeline = dados["timeline"]
    return {
        "ok": True,
        "tokens": dados["tokens"],
        "ast": dados["ast"],
        "simbolos": dados["simbolos"],
        "tom": texto_decimal(timeline.tom),
        "velocidade": texto_decimal(timeline.velocidade),
        "timeline": timeline.para_dict(),
    }
