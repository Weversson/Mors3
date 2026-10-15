import contextlib
import io
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.ast_morselang import (
    Concatenacao, Emissao, Mensagem, Programa, Referencia, Repeticao,
    Texto, Tom, Velocidade, para_dict,
)
from src.lexico import ErroLexico, analisar as analisar_lexico
from src.sintatico import ErroSintatico, analisar


ROOT = Path(__file__).resolve().parent.parent


class ProgramaTest(unittest.TestCase):
    def test_programa_minimo(self):
        resultado = analisar('emitir "SOS";')
        self.assertIsInstance(resultado.programa, Programa)
        self.assertEqual(len(resultado.programa.comandos), 1)
        self.assertIsInstance(resultado.programa.comandos[0], Emissao)
        self.assertEqual(resultado.programa.comandos[0].expressao.valor, 'SOS')
        self.assertIn('(emissao emitir', resultado.arvore)
        self.assertTrue(resultado.arvore.endswith('<EOF>)'))

    def test_exemplos_validos(self):
        for caminho in sorted((ROOT / 'exemplos').glob('*.mf')):
            with self.subTest(arquivo=caminho.name):
                programa = analisar(caminho.read_text(encoding='utf-8')).programa
                self.assertIsInstance(programa.comandos[-1], Emissao)

    def test_ola_preserva_comandos_e_valores(self):
        programa = analisar((ROOT / 'exemplos/ola.mf').read_text(encoding='utf-8')).programa
        self.assertEqual([type(c) for c in programa.comandos],
                         [Mensagem, Tom, Velocidade, Emissao])
        mensagem, tom, velocidade, emissao = programa.comandos
        self.assertEqual(mensagem.nome, 'alerta')
        self.assertEqual(mensagem.expressao.valor, 'SOS')
        self.assertEqual(tom.valor.lexema, '600.0')
        self.assertEqual(velocidade.valor.lexema, '20')
        self.assertIsInstance(emissao.expressao, Repeticao)
        self.assertEqual(emissao.expressao.quantidade.lexema, '2')

    def test_todas_as_ordens_do_preambulo(self):
        # Configurações podem faltar ou aparecer em ambas as ordens;
        # declarações podem ocupar qualquer posição antes das emissões.
        declaracoes = [('mensagem a = "A";', Mensagem),
                       ('mensagem b = "B";', Mensagem)]
        configuracoes = [('tom 700.5;', Tom), ('velocidade 18;', Velocidade)]
        for quantidade in range(3):
            for escolhidas in itertools.combinations(configuracoes, quantidade):
                for ordem in itertools.permutations([*declaracoes, *escolhidas]):
                    fonte = ' '.join(item[0] for item in ordem) + ' emitir a + b;'
                    with self.subTest(fonte=fonte):
                        comandos = analisar(fonte).programa.comandos
                        self.assertEqual([type(c) for c in comandos],
                                         [item[1] for item in ordem] + [Emissao])

    def test_tom_inteiro_e_real(self):
        for numero in ('600', '750.5'):
            with self.subTest(numero=numero):
                tom = analisar(f'tom {numero}; emitir "A";').programa.comandos[0]
                self.assertEqual(tom.valor.lexema, numero)

    def test_multiplas_emissoes(self):
        comandos = analisar('emitir "A"; emitir "B"; emitir "C";').programa.comandos
        self.assertEqual([c.expressao.valor for c in comandos], ['A', 'B', 'C'])

    def test_comentarios_unicode_e_posicoes(self):
        resultado = analisar('// início\r\n  mensagem aviso = "Olá // mundo";\r\n  emitir aviso; // fim')
        mensagem, emissao = resultado.programa.comandos
        self.assertEqual((mensagem.linha, mensagem.coluna), (2, 3))
        self.assertEqual((mensagem.expressao.linha, mensagem.expressao.coluna), (2, 20))
        self.assertEqual(mensagem.expressao.valor, 'Olá // mundo')
        self.assertEqual((emissao.linha, emissao.coluna), (3, 3))
        self.assertEqual((emissao.expressao.linha, emissao.expressao.coluna), (3, 10))

    def test_analises_independentes(self):
        with self.assertRaises(ErroSintatico):
            analisar('emitir ;')
        self.assertEqual(analisar('emitir "B";').programa.comandos[0].expressao.valor, 'B')

    def test_regras_semanticas_ficam_para_e4(self):
        # Sintaxe válida não implica nomes resolvidos, números positivos ou
        # caracteres convertíveis para Morse. O parser não executa a fonte.
        for fonte in ('emitir ausente;',
                      'mensagem a = b; mensagem b = "B"; emitir a;',
                      'mensagem a = "A"; mensagem a = "B"; emitir a;',
                      'tom 0; velocidade 0; emitir "A" * 0;',
                      'emitir "😀";', 'emitir "";'):
            with self.subTest(fonte=fonte):
                self.assertIsInstance(analisar(fonte).programa, Programa)

    def test_numeros_preservados_sem_conversao_semantica(self):
        numero = '9' * 5000
        resultado = analisar(f'emitir "E" * {numero};')
        self.assertEqual(resultado.programa.comandos[0].expressao.quantidade.lexema, numero)


class ExpressaoTest(unittest.TestCase):
    def expressao(self, fonte):
        return analisar(f'emitir {fonte};').programa.comandos[0].expressao

    def test_repeticao_tem_precedencia_sobre_concatenacao(self):
        expr = self.expressao('"A" + "B" * 2')
        self.assertIsInstance(expr, Concatenacao)
        self.assertEqual(expr.esquerda.valor, 'A')
        self.assertIsInstance(expr.direita, Repeticao)
        self.assertEqual(expr.direita.texto.valor, 'B')

    def test_parenteses_mudam_agrupamento(self):
        expr = self.expressao('("A" + "B") * 2')
        self.assertIsInstance(expr, Repeticao)
        self.assertIsInstance(expr.texto, Concatenacao)
        self.assertEqual(expr.texto.direita.valor, 'B')

    def test_concatenacao_associativa_a_esquerda(self):
        expr = self.expressao('"A" + "B" + "C"')
        self.assertIsInstance(expr.esquerda, Concatenacao)
        self.assertEqual(expr.esquerda.esquerda.valor, 'A')
        self.assertEqual(expr.esquerda.direita.valor, 'B')
        self.assertEqual(expr.direita.valor, 'C')

    def test_repeticao_associativa_a_esquerda(self):
        expr = self.expressao('"A" * 2 * 3')
        self.assertIsInstance(expr.texto, Repeticao)
        self.assertEqual(expr.texto.quantidade.lexema, '2')
        self.assertEqual(expr.quantidade.lexema, '3')

    def test_parenteses_aninhados(self):
        expr = self.expressao('((alerta + ("B" * 2))) * 3')
        self.assertIsInstance(expr, Repeticao)
        self.assertIsInstance(expr.texto.esquerda, Referencia)
        self.assertEqual(expr.texto.esquerda.nome, 'alerta')
        self.assertIsInstance(expr.texto.direita, Repeticao)

    def test_ast_json_preserva_tipo_posicao_e_texto(self):
        dados = para_dict(analisar('emitir "Olá";').programa)
        self.assertEqual(dados['tipo'], 'Programa')
        expressao = dados['comandos'][0]['expressao']
        self.assertEqual(expressao, {'tipo': 'Texto', 'linha': 1, 'coluna': 8, 'valor': 'Olá'})
        self.assertEqual(json.loads(json.dumps(dados, ensure_ascii=False)), dados)


class ErrosTest(unittest.TestCase):
    def test_entradas_lexicamente_validas_mas_sintaticamente_invalidas(self):
        casos = [
            '', '// apenas comentário', 'mensagem a = "A";', 'tom 600;',
            'emitir "A"', 'emitir ;', 'emitir 20;', 'emitir ("A";',
            'emitir "A");', 'emitir ();', 'emitir "A" + ;',
            'emitir "A" "B";', 'emitir "A" * ;', 'emitir "A" * 2.5;',
            'emitir "A" * outro;', 'emitir "A" * (2);',
            'emitir 2 * "A";', 'emitir "A" = "B";',
            'mensagem a "A"; emitir a;', 'mensagem emitir = "A"; emitir "A";',
            'mensagem a = ; emitir a;', 'velocidade 20.5; emitir "A";',
            'tom "600"; emitir "A";', 'tom 600; tom 700; emitir "A";',
            'velocidade 20; velocidade 30; emitir "A";',
            'tom 600; velocidade 20; tom 700; emitir "A";',
            'velocidade 20; tom 600; velocidade 30; emitir "A";',
            'emitir "A"; tom 600;', 'emitir "A"; velocidade 20;',
            'emitir "A"; mensagem a = "A";', 'emitir "A"; lixo',
            'emitir "A";;',
        ]
        for fonte in casos:
            with self.subTest(fonte=fonte):
                analisar_lexico(fonte)
                with self.assertRaises(ErroSintatico):
                    analisar(fonte)

    def test_erro_informa_token_esperado_e_posicao(self):
        with self.assertRaises(ErroSintatico) as erro:
            analisar('mensagem a = "A";\n  emitir (a;')
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 12))
        self.assertIn("encontrado ';'", erro.exception.detalhe)
        self.assertIn("')'", erro.exception.detalhe)

    def test_erro_no_fim_do_arquivo(self):
        with self.assertRaises(ErroSintatico) as erro:
            analisar('emitir "A"')
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (1, 11))
        self.assertIn('fim do arquivo', erro.exception.detalhe)
        self.assertIn("';'", erro.exception.detalhe)

    def test_erro_lexico_nao_e_ignorado(self):
        for fonte in ('@ emitir "A";', 'emitir "A"; @',
                      'emitir "A\\n";', 'emitir "texto sem fechar',
                      'tom 12.3.4; emitir "A";'):
            with self.subTest(fonte=fonte):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(ErroLexico):
                        analisar(fonte)
                self.assertEqual(stderr.getvalue(), '')

    def test_posicao_do_erro_lexico(self):
        with self.assertRaises(ErroLexico) as erro:
            analisar('emitir "A";\n  @')
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))

    def test_exemplos_de_erro_sintatico(self):
        caminhos = sorted((ROOT / 'exemplos/invalidos/sintaticos').glob('*.mf'))
        self.assertGreaterEqual(len(caminhos), 6)
        for caminho in caminhos:
            with self.subTest(arquivo=caminho.name):
                fonte = caminho.read_text(encoding='utf-8')
                analisar_lexico(fonte)
                with self.assertRaises(ErroSintatico):
                    analisar(fonte)


class CliSintaticoTest(unittest.TestCase):
    def executar(self, *args, cwd=ROOT):
        return subprocess.run(
            [sys.executable, str(ROOT / 'src/sintatico.py'), *map(str, args)],
            cwd=cwd, capture_output=True, text=True,
        )

    def test_programa_valido(self):
        resultado = self.executar('exemplos/ola.mf')
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn('4 comando(s)', resultado.stdout)
        self.assertEqual(resultado.stderr, '')

    def test_arvore_concreta(self):
        resultado = self.executar('exemplos/eco.mf', '--arvore')
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertTrue(resultado.stdout.startswith('(programa '))
        self.assertIn('(termo (atomo eco) * 3)', resultado.stdout)

    def test_ast_json(self):
        resultado = self.executar('exemplos/ola.mf', '--ast')
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        dados = json.loads(resultado.stdout)
        self.assertEqual(dados['tipo'], 'Programa')
        self.assertEqual(dados['comandos'][-1]['expressao']['tipo'], 'Repeticao')

    def test_erros_lexicos_e_sintaticos(self):
        casos = [('exemplos/invalidos/caractere_invalido.mf', 'erro léxico'),
                 ('exemplos/invalidos/sintaticos/sem_ponto_virgula.mf', 'erro sintático')]
        for caminho, categoria in casos:
            with self.subTest(caminho=caminho):
                resultado = self.executar(caminho, '--ast')
                self.assertEqual(resultado.returncode, 1)
                self.assertEqual(resultado.stdout, '')
                self.assertIn(categoria, resultado.stderr)
                self.assertIn('linha', resultado.stderr)
                self.assertIn('coluna', resultado.stderr)
                self.assertNotIn('Traceback', resultado.stderr)

    def test_arquivo_inexistente_e_utf8_invalido(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'entrada.mf'
            resultado = self.executar(caminho)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('não foi possível ler', resultado.stderr)
            caminho.write_bytes(b'\xff')
            resultado = self.executar(caminho)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('não foi possível ler', resultado.stderr)
            self.assertNotIn('Traceback', resultado.stderr)

    def test_execucao_fora_do_projeto_sem_gerar_audio(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / 'entrada.mf'
            fonte.write_text('emitir "SOS";', encoding='utf-8')
            resultado = self.executar(fonte, '--ast', cwd=pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertEqual(json.loads(resultado.stdout)['tipo'], 'Programa')
            self.assertEqual(sorted(p.name for p in Path(pasta).iterdir()), ['entrada.mf'])

    def test_execucao_como_modulo(self):
        resultado = subprocess.run(
            [sys.executable, '-m', 'src.sintatico', 'exemplos/eco.mf'],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn('sintaticamente válido', resultado.stdout)

    def test_opcoes_cli(self):
        self.assertEqual(self.executar('--help').returncode, 0)
        self.assertEqual(self.executar().returncode, 2)
        self.assertEqual(self.executar('exemplos/ola.mf', '--ast', '--arvore').returncode, 2)


if __name__ == '__main__':
    unittest.main()
