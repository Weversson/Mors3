"""Verificador genérico de um arquivo, chamado pelo orquestrador shell.

Não contém programas de teste nem listas de nomes. As expectativas vêm da
classe recebida e, opcionalmente, de um JSON ao lado do arquivo .mf.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ast_morselang import para_dict
from src.lexico import ErroLexico, criar_lexer
from src.sintatico import ErroSintatico, analisar


def sem_posicoes(valor):
    """Compara a estrutura da AST independentemente de espaços e comentários."""
    if isinstance(valor, dict):
        return {chave: sem_posicoes(item) for chave, item in valor.items()
                if chave not in ('linha', 'coluna')}
    if isinstance(valor, list):
        return [sem_posicoes(item) for item in valor]
    return valor


def tempo_esgotado(signum, frame):
    raise TimeoutError('tempo limite do caso excedido')


def executar(args):
    inicio = time.perf_counter()
    registro = {'arquivo': str(args.arquivo.resolve()), 'nome': args.nome,
                'classe': args.classe, 'aprovado': False}
    signal.signal(signal.SIGALRM, tempo_esgotado)
    signal.setitimer(signal.ITIMER_REAL, args.timeout)
    try:
        conteudo = args.arquivo.read_bytes()
        registro['sha256'] = hashlib.sha256(conteudo).hexdigest()
        fonte = conteudo.decode('utf-8')
        registro['entrada'] = fonte
        metadados = args.arquivo.with_suffix('.json')
        esperado = json.loads(metadados.read_text(encoding='utf-8')) if metadados.exists() else {}
        if not isinstance(esperado, dict) or set(esperado) - {'ast', 'erro'}:
            raise ValueError('expectativa deve conter somente ast ou erro')
        if ('ast' in esperado and args.classe != 'validas') or ('erro' in esperado and args.classe != 'invalidas'):
            raise ValueError('expectativa incompatível com a pasta de classificação')
        registro['expectativa_adicional'] = esperado

        # Pré-condição da suíte: todos os arquivos têm tokens válidos.
        # Um ErroLexico aqui denuncia um caso fora do escopo do parser.
        criar_lexer(fonte).getAllTokens()
        try:
            resultado = analisar(fonte)
        except ErroSintatico as erro:
            registro['observado'] = {'tipo': 'erro_sintatico', 'linha': erro.linha,
                                     'coluna': erro.coluna, 'detalhe': erro.detalhe}
            if args.classe != 'invalidas':
                raise AssertionError(f'entrada válida rejeitada: {erro}')
            if 'erro' in esperado:
                if not isinstance(esperado['erro'], dict) or not esperado['erro']:
                    raise ValueError('a expectativa de erro deve ser um objeto não vazio')
                for chave, valor in esperado['erro'].items():
                    if chave not in registro['observado'] or registro['observado'][chave] != valor:
                        raise AssertionError(f'erro com {chave} diferente do esperado: {valor!r}')
        else:
            ast = sem_posicoes(para_dict(resultado.programa))
            registro['observado'] = {'tipo': 'aceito', 'ast': ast, 'arvore': resultado.arvore}
            if args.classe != 'validas':
                raise AssertionError('entrada inválida aceita pelo parser')
            if 'ast' in esperado and ast != esperado['ast']:
                raise AssertionError('AST diferente da expectativa externa')
        registro['aprovado'] = True
    except ErroLexico as erro:
        registro['falha'] = f'entrada fora do escopo: erro léxico: {erro}'
    except Exception as erro:
        # Inclui timeout, erro de leitura, JSON incorreto e falha interna.
        registro['falha'] = f'{type(erro).__name__}: {erro}'
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    registro['duracao_segundos'] = round(time.perf_counter() - inicio, 6)
    with args.resultados.open('a', encoding='utf-8') as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + '\n')
    if not registro['aprovado']:
        print(registro['falha'], file=sys.stderr)
    return 0 if registro['aprovado'] else 1


def resumir(args):
    registros = [json.loads(linha) for linha in args.resultados.read_text(encoding='utf-8').splitlines()]
    falhas = [r for r in registros if not r['aprovado']]
    resumo = {
        'descobertos': args.total, 'registrados': len(registros),
        'aprovados': len(registros) - len(falhas), 'falhas': len(falhas),
        'duracao_segundos': args.duracao,
        'por_classe': {classe: sum(r['classe'] == classe for r in registros)
                       for classe in ('validas', 'invalidas')},
        'comparacoes_ast': sum('ast' in r.get('expectativa_adicional', {}) for r in registros),
        'comparacoes_erro': sum('erro' in r.get('expectativa_adicional', {}) for r in registros),
        'arquivos_com_falha': [r['arquivo'] for r in falhas],
    }
    destino = args.resultados.with_name('resumo.json')
    destino.write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(f'Resumo salvo em: {destino}')
    return 0 if registros and len(registros) == args.total and not falhas else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest='comando', required=True)
    preparar = comandos.add_parser('preparar')
    preparar.add_argument('--timeout', type=float, required=True)
    caso = comandos.add_parser('caso')
    caso.add_argument('--arquivo', type=Path, required=True)
    caso.add_argument('--nome', required=True)
    caso.add_argument('--classe', choices=('validas', 'invalidas'), required=True)
    caso.add_argument('--timeout', type=float, required=True)
    caso.add_argument('--resultados', type=Path, required=True)
    resumo = comandos.add_parser('resumir')
    resumo.add_argument('--resultados', type=Path, required=True)
    resumo.add_argument('--total', type=int, required=True)
    resumo.add_argument('--duracao', type=float, required=True)
    args = parser.parse_args()
    if hasattr(args, 'timeout') and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error('--timeout deve ser positivo e finito')
    if args.comando == 'preparar':
        return 0
    return executar(args) if args.comando == 'caso' else resumir(args)


if __name__ == '__main__':
    raise SystemExit(main())
