"""Testes do analisador léxico modular de MorseLang (E2)."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.analise_lexica import (
    ErroLexico,
    TokenInfo,
    analisar,
    criar_lexer,
    iterar_tokens,
)
from src.analise_lexica.cli import main


ROOT = Path(__file__).resolve().parent.parent
EXEMPLOS = ROOT / "exemplos"


def executar(*args, cwd=ROOT):
    """Executa a CLI histórica `src/lexico.py` em um subprocesso."""
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "lexico.py"), *map(str, args)],
        text=True,
        capture_output=True,
        cwd=cwd,
    )


def executar_modulo(modulo, *args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, "-m", modulo, *map(str, args)],
        text=True,
        capture_output=True,
        cwd=cwd,
    )


def tipos(tokens):
    return [token.tipo for token in tokens]


def textos(tokens):
    return [token.texto for token in tokens]


class ModeloTest(unittest.TestCase):
    def test_token_info_e_imutavel_e_formatado(self):
        token = TokenInfo("TEXTO", '"SOS"', 2, 8)
        self.assertEqual(token, TokenInfo("TEXTO", '"SOS"', 2, 8))
        self.assertEqual(token.formatar(), "TEXTO '\"SOS\"' linha 2 coluna 8")
        with self.assertRaises(AttributeError):
            token.linha = 3

    def test_fonte_vazia_e_somente_espacos(self):
        for fonte in ("", " \t\r\n", "// comentário\n", "  // a\r\n\t// b"):
            with self.subTest(fonte=fonte):
                self.assertEqual(analisar(fonte), [])

    def test_analisar_devolve_lista_e_iterar_devolve_gerador(self):
        self.assertIsInstance(analisar('emitir "A";'), list)
        tokens = iterar_tokens('emitir "A";')
        self.assertIs(iter(tokens), tokens)
        self.assertEqual(tipos(tokens), ["EMITIR", "TEXTO", "PONTO_VIRGULA"])

    def test_analises_independentes(self):
        self.assertEqual(tipos(analisar('emitir "A";')),
                         ["EMITIR", "TEXTO", "PONTO_VIRGULA"])
        self.assertEqual(tipos(analisar('tom 600;')),
                         ["TOM", "INTEIRO", "PONTO_VIRGULA"])

    def test_criar_lexer_rejeita_texto_que_nao_e_str(self):
        with self.assertRaises(TypeError):
            criar_lexer(b'emitir "A";')


class CategoriasTest(unittest.TestCase):
    def test_palavras_chave(self):
        tokens = analisar("mensagem tom velocidade emitir")
        self.assertEqual(tipos(tokens),
                         ["MENSAGEM", "TOM", "VELOCIDADE", "EMITIR"])
        self.assertEqual(textos(tokens),
                         ["mensagem", "tom", "velocidade", "emitir"])

    def test_identificadores_e_limites_das_palavras_chave(self):
        tokens = analisar("mensagem mensagem_extra tomate _a a1 A_b2")
        self.assertEqual(tipos(tokens),
                         ["MENSAGEM", "IDENT", "IDENT", "IDENT", "IDENT",
                          "IDENT"])
        self.assertEqual(textos(tokens),
                         ["mensagem", "mensagem_extra", "tomate", "_a", "a1",
                          "A_b2"])

    def test_pontuacao(self):
        tokens = analisar("= + * ( ) ;")
        self.assertEqual(tipos(tokens),
                         ["IGUAL", "MAIS", "VEZES", "ABRE_PAR", "FECHA_PAR",
                          "PONTO_VIRGULA"])
        self.assertEqual(textos(tokens), ["=", "+", "*", "(", ")", ";"])

    def test_inteiros_e_reais_preservam_o_lexema(self):
        tokens = analisar("0 007 600.0 0.50")
        self.assertEqual(tipos(tokens), ["INTEIRO", "INTEIRO", "REAL", "REAL"])
        self.assertEqual(textos(tokens), ["0", "007", "600.0", "0.50"])

    def test_textos_vazio_unicode_e_simbolos(self):
        tokens = analisar('"" "SOS" "Olá 😀 + * ; // x"')
        self.assertEqual(tipos(tokens), ["TEXTO", "TEXTO", "TEXTO"])
        self.assertEqual(textos(tokens),
                         ['""', '"SOS"', '"Olá 😀 + * ; // x"'])

    def test_comentarios_e_espacos_sao_descartados(self):
        tokens = analisar('// ignorado\n  emitir "//"; // ignorado\n')
        self.assertEqual(tipos(tokens), ["EMITIR", "TEXTO", "PONTO_VIRGULA"])
        self.assertEqual((tokens[0].linha, tokens[0].coluna), (2, 3))
        self.assertEqual(tokens[1].texto, '"//"')

    def test_posicoes_em_lf_crlf_e_apos_unicode(self):
        tokens = analisar('  emitir\r\n\t"SOS";\nemitir "Olá"; mensagem')
        self.assertEqual(
            [(t.tipo, t.linha, t.coluna) for t in tokens],
            [("EMITIR", 1, 3), ("TEXTO", 2, 2), ("PONTO_VIRGULA", 2, 7),
             ("EMITIR", 3, 1), ("TEXTO", 3, 8), ("PONTO_VIRGULA", 3, 13),
             ("MENSAGEM", 3, 15)],
        )


class ErrosTest(unittest.TestCase):
    def assert_erro(self, fonte, linha, coluna):
        with self.assertRaises(ErroLexico) as contexto:
            analisar(fonte)
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn("não reconhecido", erro.detalhe)
        return erro

    def test_caracteres_fora_da_linguagem(self):
        for fonte, coluna in (("@", 1), (" -1", 2), ("#", 1), (".", 1),
                              ("emitir @", 8)):
            with self.subTest(fonte=fonte):
                self.assert_erro(fonte, 1, coluna)

    def test_texto_sem_fechamento(self):
        for fonte, linha, coluna in (('"SOS', 1, 1), ('emitir "SOS;', 1, 8),
                                     ('\n  "SOS', 2, 3)):
            with self.subTest(fonte=fonte):
                self.assert_erro(fonte, linha, coluna)

    def test_texto_com_quebra_de_linha_ou_barra_invertida(self):
        self.assert_erro('emitir "a\nb";', 1, 8)
        self.assert_erro('emitir "a\\b";', 1, 8)

    def test_numeros_malformados(self):
        for fonte, coluna in (("1..2", 2), ("1.", 2), (".5", 1),
                              ("1.2.3", 4), ("tom 600..5;", 8)):
            with self.subTest(fonte=fonte):
                self.assert_erro(fonte, 1, coluna)

    def test_posicao_apos_linha_e_comentario(self):
        self.assert_erro('emitir "OK";\n  // comentário\n  @', 3, 3)

    def test_primeiro_erro_interrompe_a_analise(self):
        erro = self.assert_erro("@ #", 1, 1)
        self.assertIn("'@'", erro.detalhe)

    def test_erro_nao_escreve_em_stderr(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(ErroLexico):
                analisar("@")
        self.assertEqual(stderr.getvalue(), "")

    def test_criar_lexer_tambem_falha_no_primeiro_erro(self):
        with self.assertRaises(ErroLexico) as contexto:
            criar_lexer("emitir @").getAllTokens()
        self.assertEqual((contexto.exception.linha, contexto.exception.coluna),
                         (1, 8))


class ExemplosTest(unittest.TestCase):
    def test_todos_os_exemplos_validos(self):
        caminhos = sorted(EXEMPLOS.glob("*.mf"))
        self.assertGreaterEqual(len(caminhos), 5)
        for caminho in caminhos:
            with self.subTest(arquivo=caminho.name):
                tokens = analisar(caminho.read_text(encoding="utf-8"))
                self.assertGreater(len(tokens), 0)
                self.assertIn("EMITIR", tipos(tokens))

    def test_exemplos_invalidos_com_posicao(self):
        invalidos = {
            "caractere_invalido.mf": (1, 14),
            "texto_sem_fechar.mf": (1, 8),
            "numero_malformado.mf": (1, 8),
        }
        for nome, (linha, coluna) in invalidos.items():
            with self.subTest(nome=nome):
                fonte = (EXEMPLOS / "invalidos" / nome).read_text(
                    encoding="utf-8")
                with self.assertRaises(ErroLexico) as contexto:
                    analisar(fonte)
                self.assertEqual(
                    (contexto.exception.linha, contexto.exception.coluna),
                    (linha, coluna),
                )

    def test_exemplos_sintaticos_invalidos_sao_lexicamente_validos(self):
        caminhos = sorted((EXEMPLOS / "invalidos" / "sintaticos").glob("*.mf"))
        self.assertGreaterEqual(len(caminhos), 6)
        for caminho in caminhos:
            with self.subTest(arquivo=caminho.name):
                tokens = analisar(caminho.read_text(encoding="utf-8"))
                self.assertGreater(len(tokens), 0)


class CliTest(unittest.TestCase):
    def test_programa_valido(self):
        resultado = executar(EXEMPLOS / "ola.mf")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stderr, "")
        self.assertIn("MENSAGEM 'mensagem' linha 2 coluna 1", resultado.stdout)
        self.assertIn("tokens reconhecidos", resultado.stdout)
        self.assertNotIn("COMENTARIO", resultado.stdout)
        self.assertNotIn("ESPACO", resultado.stdout)

    def test_erro_lexico_nao_imprime_tokens(self):
        resultado = executar(EXEMPLOS / "invalidos" / "caractere_invalido.mf")
        self.assertEqual(resultado.returncode, 1)
        self.assertEqual(resultado.stdout, "")
        self.assertIn("erro léxico: linha 1, coluna 14", resultado.stderr)
        self.assertIn("não reconhecido", resultado.stderr)

    def test_arquivo_inexistente_e_utf8_invalido(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "entrada.mf"
            resultado = executar(caminho)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn("não foi possível ler", resultado.stderr)

            caminho.write_bytes(b"\xff")
            resultado = executar(caminho)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn("não foi possível ler", resultado.stderr)
            self.assertNotIn("Traceback", resultado.stderr)

    def test_uso_incorreto_e_ajuda(self):
        self.assertEqual(executar().returncode, 2)
        resultado = executar("--help")
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("Lista os tokens", resultado.stdout)

    def test_execucao_como_modulo_historico_e_do_pacote(self):
        for modulo in ("src.lexico", "src.analise_lexica"):
            with self.subTest(modulo=modulo):
                resultado = executar_modulo(modulo, "exemplos/ola.mf")
                self.assertEqual(resultado.returncode, 0, resultado.stderr)
                self.assertIn("tokens reconhecidos", resultado.stdout)

    def test_execucao_fora_do_projeto(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text('emitir "SOS";', encoding="utf-8")
            resultado = executar(fonte, cwd=pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertIn("EMITIR 'emitir' linha 1 coluna 1",
                          resultado.stdout)

    def test_main_recebe_saidas_injetadas(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text('emitir "SOS";', encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            retorno = main([str(fonte)], stdout=stdout, stderr=stderr)
            self.assertEqual(retorno, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("3 tokens reconhecidos", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
