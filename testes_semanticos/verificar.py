"""Verificador de um caso semântico, chamado pelo orquestrador shell.

O verificador executa a cadeia léxica -> sintática -> semântica e compara o
resultado com a classificação da pasta e com um JSON opcional ao lado do `.mf`.
Uma entrada do corpus semântico precisa passar pelo lexer e pelo parser; a
diferença observada deve ser necessariamente um erro semântico.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analise_lexica import ErroLexico
from src.semantico import ErroSemantico, analisar_fonte
from src.sintatico import ErroSintatico


CAMPOS_VALIDOS = {"tom", "velocidade", "emissoes", "mensagens"}
CAMPOS_ERRO = {"linha", "coluna", "detalhe", "detalhe_contem"}


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{campo} deve ser um número: {valor!r}") from None


def _numero(valor):
    return format(valor, "f")


def _validar_expectativa(esperado, classe):
    if not isinstance(esperado, dict):
        raise ValueError("a expectativa deve ser um objeto JSON")
    permitidos = CAMPOS_VALIDOS if classe == "validas" else {"erro"}
    desconhecidos = set(esperado) - permitidos
    if desconhecidos:
        raise ValueError(
            f"expectativa incompatível com a classe {classe}: "
            f"{', '.join(sorted(desconhecidos))}")
    if classe == "invalidas" and "erro" in esperado:
        erro = esperado["erro"]
        if not isinstance(erro, dict) or not erro:
            raise ValueError("a expectativa de erro deve ser um objeto não vazio")
        desconhecidos = set(erro) - CAMPOS_ERRO
        if desconhecidos:
            raise ValueError(
                f"campos de erro desconhecidos: {', '.join(sorted(desconhecidos))}")


def _conferir_sucesso(resultado, esperado, registro):
    observado = {
        "tipo": "aceito",
        "tom": _numero(resultado.tom),
        "velocidade": _numero(resultado.velocidade),
        "emissoes": len(resultado.emissoes),
        "mensagens": len(resultado.mensagens),
    }
    registro["observado"] = observado

    for campo in ("tom", "velocidade"):
        if campo in esperado:
            if Decimal(observado[campo]) != _decimal(esperado[campo], campo):
                raise AssertionError(
                    f"{campo} diferente do esperado: {esperado[campo]!r}")
    for campo in ("emissoes", "mensagens"):
        if campo in esperado and observado[campo] != esperado[campo]:
            raise AssertionError(
                f"{campo} diferente do esperado: {esperado[campo]!r}")


def _conferir_erro(erro, esperado, registro):
    observado = {
        "tipo": "erro_semantico",
        "linha": erro.linha,
        "coluna": erro.coluna,
        "detalhe": erro.detalhe,
    }
    registro["observado"] = observado
    esperado_erro = esperado.get("erro", {})

    for campo in ("linha", "coluna", "detalhe"):
        if campo in esperado_erro and observado[campo] != esperado_erro[campo]:
            raise AssertionError(
                f"erro com {campo} diferente do esperado: "
                f"{esperado_erro[campo]!r}")
    if "detalhe_contem" in esperado_erro:
        trecho = esperado_erro["detalhe_contem"]
        if not isinstance(trecho, str) or trecho not in observado["detalhe"]:
            raise AssertionError(
                f"detalhe não contém o trecho esperado: {trecho!r}")


def tempo_esgotado(signum, frame):
    raise TimeoutError("tempo limite do caso excedido")


def executar(args):
    inicio = time.perf_counter()
    registro = {
        "arquivo": str(args.arquivo.resolve()),
        "nome": args.nome,
        "classe": args.classe,
        "aprovado": False,
    }
    signal.signal(signal.SIGALRM, tempo_esgotado)
    signal.setitimer(signal.ITIMER_REAL, args.timeout)
    try:
        conteudo = args.arquivo.read_bytes()
        registro["sha256"] = hashlib.sha256(conteudo).hexdigest()
        fonte = conteudo.decode("utf-8")
        registro["entrada"] = fonte

        metadados = args.arquivo.with_suffix(".json")
        esperado = (json.loads(metadados.read_text(encoding="utf-8"))
                    if metadados.exists() else {})
        _validar_expectativa(esperado, args.classe)
        registro["expectativa_adicional"] = esperado

        try:
            resultado = analisar_fonte(fonte)
        except ErroSemantico as erro:
            _conferir_erro(erro, esperado, registro)
            if args.classe != "invalidas":
                raise AssertionError(f"entrada válida rejeitada: {erro}")
        except (ErroLexico, ErroSintatico) as erro:
            # O corpus é semântico: falhas anteriores à E4 são erro de escopo,
            # nunca uma rejeição semântica válida.
            raise AssertionError(
                f"entrada fora do escopo semântico: "
                f"{type(erro).__name__}: {erro}") from None
        else:
            _conferir_sucesso(resultado, esperado, registro)
            if args.classe != "validas":
                raise AssertionError("entrada inválida aceita pela análise semântica")

        registro["aprovado"] = True
    except Exception as erro:
        registro["falha"] = f"{type(erro).__name__}: {erro}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

    registro["duracao_segundos"] = round(time.perf_counter() - inicio, 6)
    with args.resultados.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    if not registro["aprovado"]:
        print(registro["falha"], file=sys.stderr)
    return 0 if registro["aprovado"] else 1


def resumir(args):
    registros = [
        json.loads(linha)
        for linha in args.resultados.read_text(encoding="utf-8").splitlines()
    ]
    falhas = [r for r in registros if not r["aprovado"]]
    resumo = {
        "descobertos": args.total,
        "registrados": len(registros),
        "aprovados": len(registros) - len(falhas),
        "falhas": len(falhas),
        "duracao_segundos": args.duracao,
        "por_classe": {
            classe: sum(r["classe"] == classe for r in registros)
            for classe in ("validas", "invalidas")
        },
        "comparacoes_configuracao": sum(
            bool(CAMPOS_VALIDOS & set(r.get("expectativa_adicional", {})))
            for r in registros
        ),
        "comparacoes_erro": sum(
            "erro" in r.get("expectativa_adicional", {}) for r in registros
        ),
        "arquivos_com_falha": [r["arquivo"] for r in falhas],
    }
    destino = args.resultados.with_name("resumo.json")
    destino.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(f"Resumo salvo em: {destino}")
    return (0 if registros and len(registros) == args.total and not falhas
            else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)

    caso = comandos.add_parser("caso")
    caso.add_argument("--arquivo", type=Path, required=True)
    caso.add_argument("--nome", required=True)
    caso.add_argument("--classe", choices=("validas", "invalidas"),
                      required=True)
    caso.add_argument("--timeout", type=float, required=True)
    caso.add_argument("--resultados", type=Path, required=True)

    resumo = comandos.add_parser("resumir")
    resumo.add_argument("--resultados", type=Path, required=True)
    resumo.add_argument("--total", type=int, required=True)
    resumo.add_argument("--duracao", type=float, required=True)

    args = parser.parse_args()
    if hasattr(args, "timeout") and (
            not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("--timeout deve ser positivo e finito")
    return executar(args) if args.comando == "caso" else resumir(args)


if __name__ == "__main__":
    raise SystemExit(main())
