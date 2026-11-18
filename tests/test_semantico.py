"""Testes da análise semântica modular de MorseLang (E4)."""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.analise_lexica import ErroLexico
from src.analise_semantica import (
    AnalisadorSemantico,
    ErroSemantico,
    ResultadoSemantico,
    TOM_MAXIMO,
    TOM_MINIMO,
    TOM_PADRAO,
    VELOCIDADE_PADRAO,
    analisar,
    analisar_fonte,
)
from src.analise_semantica.cli import main
from src.ast_morselang import Emissao, Mensagem
from src.sintatico import ErroSintatico, analisar as analisar_sintatico


ROOT = Path(__file__).resolve().parent.parent
EXEMPLOS = ROOT / "exemplos"
SEMANTICOS = EXEMPLOS / "invalidos" / "semanticos"


def executar(*args, cwd=ROOT):
    """Executa a CLI canônica `src/semantico.py` em um subprocesso."""
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "semantico.py"), *map(str, args)],
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


class ModeloTest(unittest.TestCase):
    def test_constantes_da_linguagem(self):
        self.assertEqual(TOM_PADRAO, Decimal("600"))
        self.assertEqual(VELOCIDADE_PADRAO, Decimal("20"))
        self.assertEqual(TOM_MINIMO, Decimal("100"))
        self.assertEqual(TOM_MAXIMO, Decimal("20000"))

    def test_resultado_expoe_configuracoes_e_comandos_resolvidos(self):
        resultado = analisar_fonte(
            'mensagem a = "A"; tom 700.5; velocidade 18; emitir a;'
        )
        self.assertIsInstance(resultado, ResultadoSemantico)
        self.assertEqual(resultado.tom, Decimal("700.5"))
        self.assertEqual(resultado.velocidade, Decimal("18"))
        self.assertEqual(resultado.tom_hz, resultado.tom)
        self.assertEqual(resultado.velocidade_wpm, resultado.velocidade)
        self.assertEqual(resultado.quantidade_emissoes, 1)
        self.assertEqual(len(resultado.mensagens), 1)
        self.assertIsInstance(resultado.mensagens[0], Mensagem)
        self.assertIsInstance(resultado.emissoes[0], Emissao)

    def test_resultado_e_imutavel(self):
        resultado = analisar_fonte('emitir "A";')
        with self.assertRaises(AttributeError):
            resultado.tom = Decimal("700")

    def test_analisar_rejeita_objetos_que_nao_sao_programa(self):
        for valor in (None, "emitir \"A\";", Emissao(linha=1, coluna=1,
                                                     expressao=None)):
            with self.subTest(valor=type(valor).__name__):
                with self.assertRaises(TypeError):
                    analisar(valor)

    def test_mesma_instancia_analisa_programas_independentes(self):
        analisador = AnalisadorSemantico()
        primeiro = analisador.analisar(
            analisar_sintatico('tom 700; emitir "A";').programa)
        segundo = analisador.analisar(
            analisar_sintatico('emitir "B";').programa)

        self.assertEqual(primeiro.tom, Decimal("700"))
        self.assertEqual(segundo.tom, TOM_PADRAO)
        self.assertEqual(segundo.mensagens, ())
        self.assertEqual(segundo.quantidade_emissoes, 1)


class ProgramasValidosTest(unittest.TestCase):
    def test_padroes_quando_configuracoes_sao_omitidas(self):
        resultado = analisar_fonte('emitir "SOS";')
        self.assertEqual(resultado.tom, Decimal("600"))
        self.assertEqual(resultado.velocidade, Decimal("20"))
        self.assertEqual(resultado.mensagens, ())
        self.assertEqual(resultado.quantidade_emissoes, 1)

    def test_configuracoes_explicitas_em_qualquer_ordem(self):
        fontes = (
            'tom 700; velocidade 18; emitir "A";',
            'velocidade 18; tom 700; emitir "A";',
            'mensagem a = "A"; tom 700; mensagem b = "B"; '
            'velocidade 18; emitir a; emitir b;',
        )
        for fonte in fontes:
            with self.subTest(fonte=fonte):
                resultado = analisar_fonte(fonte)
                self.assertEqual(resultado.tom, Decimal("700"))
                self.assertEqual(resultado.velocidade, Decimal("18"))

    def test_configuracao_unica_permanece_no_resultado(self):
        programa = analisar_sintatico('tom 600; emitir "A";').programa
        resultado = analisar(programa)
        self.assertEqual(resultado.tom, Decimal("600"))

    def test_nomes_resolvidos_em_declaracoes_e_emissoes(self):
        resultado = analisar_fonte(
            'mensagem a = "A";\n'
            'mensagem b = a + "B";\n'
            'emitir (b + a) * 3;'
        )
        self.assertEqual([m.nome for m in resultado.mensagens], ["a", "b"])
        self.assertEqual(resultado.quantidade_emissoes, 1)

    def test_repeticao_positiva_com_zeros_a_esquerda(self):
        for quantidade in ("1", "2", "007", "00010"):
            with self.subTest(quantidade=quantidade):
                resultado = analisar_fonte(f'emitir "A" * {quantidade};')
                self.assertEqual(resultado.quantidade_emissoes, 1)

    def test_repeticao_gigante_nao_e_convertida_para_inteiro(self):
        quantidade = "9" * 5000
        resultado = analisar_fonte(f'emitir "E" * {quantidade};')
        self.assertEqual(
            resultado.emissoes[0].expressao.quantidade.lexema, quantidade)

    def test_limites_de_tom_sao_inclusivos(self):
        for tom in ("100", "100.0", "600", "750.5", "20000", "20000.0"):
            with self.subTest(tom=tom):
                self.assertEqual(
                    analisar_fonte(f'tom {tom}; emitir "A";').tom,
                    Decimal(tom),
                )

    def test_velocidade_aceita_qualquer_inteiro_positivo(self):
        for velocidade in ("1", "007", "20", "99999999999999999999"):
            with self.subTest(velocidade=velocidade):
                self.assertEqual(
                    analisar_fonte(
                        f'velocidade {velocidade}; emitir "A";'
                    ).velocidade,
                    Decimal(velocidade),
                )

    def test_texto_aceita_acentos_pontuacao_espacos_e_texto_vazio(self):
        for texto in ('""', '"Ação ção ÇÃO"', '"A-Z .,?!()/@&:;=+_"',
                      '"A\tB"', '"  espaços  "', '"1234567890"'):
            with self.subTest(texto=texto):
                self.assertEqual(analisar_fonte(f"emitir {texto};")
                                 .quantidade_emissoes, 1)

    def test_todos_os_exemplos_do_projeto_sao_semanticamente_validos(self):
        caminhos = sorted(EXEMPLOS.glob("*.mf"))
        self.assertGreaterEqual(len(caminhos), 5)
        for caminho in caminhos:
            with self.subTest(arquivo=caminho.name):
                resultado = analisar_fonte(
                    caminho.read_text(encoding="utf-8"))
                self.assertGreaterEqual(resultado.quantidade_emissoes, 1)

    def test_exemplos_validos_tem_configuracoes_esperadas(self):
        esperados = {
            "ola.mf": (Decimal("600.0"), Decimal("20"), 1),
            "aviso.mf": (Decimal("750.5"), Decimal("18"), 1),
            "eco.mf": (Decimal("600"), Decimal("20"), 1),
            "multiplas_emissoes.mf": (Decimal("750.5"), Decimal("18"), 2),
            "precedencia.mf": (Decimal("600"), Decimal("20"), 2),
        }
        for nome, (tom, velocidade, emissoes) in esperados.items():
            with self.subTest(arquivo=nome):
                resultado = analisar_fonte(
                    (EXEMPLOS / nome).read_text(encoding="utf-8"))
                self.assertEqual(resultado.tom, tom)
                self.assertEqual(resultado.velocidade, velocidade)
                self.assertEqual(resultado.quantidade_emissoes, emissoes)


class NomesTest(unittest.TestCase):
    def assert_erro(self, fonte, linha, coluna, trecho):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(fonte)
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn(trecho, erro.detalhe)
        return erro

    def test_nome_precisa_ser_declarado_antes_do_uso(self):
        self.assert_erro(
            'mensagem a = b; mensagem b = "B"; emitir a;',
            1, 14, "'b' não foi declarado",
        )

    def test_referencia_ausente_na_emissao(self):
        self.assert_erro('emitir ausente;', 1, 8,
                         "'ausente' não foi declarado")

    def test_nome_nao_declarado_dentro_de_expressao_aninhada(self):
        self.assert_erro(
            'mensagem a = "A"; emitir (a + ausente) * 2;',
            1, 31, "'ausente' não foi declarado",
        )

    def test_redefinicao(self):
        self.assert_erro(
            'mensagem alerta = "SOS";\nmensagem alerta = "ECHO";\nemitir alerta;',
            2, 1, "já foi declarado",
        )

    def test_redefinicao_e_verificada_antes_da_expressao_da_nova_mensagem(self):
        # O erro esperado é o nome repetido, não o caractere sem Morse no
        # lado direito da segunda declaração.
        self.assert_erro(
            'mensagem a = "A";\nmensagem a = "😀";\nemitir a;',
            2, 1, "já foi declarado",
        )

    def test_nomes_sao_senssiveis_a_maiusculas(self):
        self.assert_erro(
            'mensagem A = "A"; emitir a;',
            1, 26, "'a' não foi declarado",
        )

    def test_autoreferencia_na_declaracao_nao_encontra_o_proprio_nome(self):
        self.assert_erro(
            'mensagem a = a; emitir a;',
            1, 14, "'a' não foi declarado",
        )


class RepeticaoTest(unittest.TestCase):
    def assert_erro(self, fonte, linha, coluna):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(fonte)
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn("inteiro positivo", erro.detalhe)
        return erro

    def test_quantidade_zero_e_rejeitada(self):
        for quantidade in ("0", "00", "0000"):
            with self.subTest(quantidade=quantidade):
                self.assert_erro(f'emitir "A" * {quantidade};', 1, 14)

    def test_posicao_do_erro_aponta_para_a_quantidade(self):
        self.assert_erro('emitir "A"\n  * 0;', 2, 5)

    def test_erro_na_quantidade_de_uma_repeticao_aninhada(self):
        self.assert_erro('emitir ("A" * 0) * 2;', 1, 15)

    def test_texto_invalido_e_verificado_antes_da_quantidade(self):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte('emitir "😀" * 0;')
        self.assertIn("não possui representação em Morse",
                      contexto.exception.detalhe)


class TomTest(unittest.TestCase):
    def assert_erro(self, tom, linha, coluna):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(f'tom {tom};\nemitir "A";')
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn("entre 100 e 20000 Hz", erro.detalhe)
        return erro

    def test_tom_abaixo_do_minimo(self):
        for tom in ("0", "0.0", "99", "99.999"):
            with self.subTest(tom=tom):
                self.assert_erro(tom, 1, 5)

    def test_tom_acima_do_maximo(self):
        for tom in ("20000.1", "20001", "25000", "999999"):
            with self.subTest(tom=tom):
                self.assert_erro(tom, 1, 5)

    def test_detalhe_preserva_o_lexema(self):
        erro = self.assert_erro("25000", 1, 5)
        self.assertIn("25000", erro.detalhe)


class VelocidadeTest(unittest.TestCase):
    def assert_erro(self, velocidade):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(f'velocidade {velocidade};\nemitir "A";')
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (1, 12))
        self.assertIn("inteiro positivo", erro.detalhe)
        return erro

    def test_velocidade_zero_e_rejeitada(self):
        for velocidade in ("0", "00", "0000"):
            with self.subTest(velocidade=velocidade):
                self.assert_erro(velocidade)

    def test_detalhe_trunca_lexemas_muito_grandes(self):
        erro = self.assert_erro("0" * 100)
        self.assertIn("...", erro.detalhe)
        self.assertLess(len(erro.detalhe), 120)


class TextoTest(unittest.TestCase):
    def assert_erro(self, fonte, linha, coluna, caractere):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(fonte)
        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (linha, coluna))
        self.assertIn(f"o caractere {caractere!r}", erro.detalhe)
        self.assertIn("não possui representação em Morse", erro.detalhe)
        return erro

    def test_caractere_sem_morse_na_emissao(self):
        self.assert_erro('emitir "SOS 😀";', 1, 13, "😀")

    def test_caractere_sem_morse_em_declaracao_nunca_emitida(self):
        # Toda expressão é validada, mesmo que a mensagem não seja usada.
        self.assert_erro(
            'mensagem nao_usada = "A😀";\nemitir "SOS";',
            1, 24, "😀",
        )

    def test_caractere_sem_morse_no_meio_da_concatenacao(self):
        self.assert_erro(
            'emitir "A" + "B中" + "C";',
            1, 16, "中",
        )

    def test_emojis_e_simbolos_sem_representacao(self):
        for caractere in ("😀", "中", "€", "\u200b"):
            with self.subTest(caractere=caractere):
                self.assert_erro(f'emitir "{caractere}";', 1, 9, caractere)


class PrimeiroErroTest(unittest.TestCase):
    def test_analise_para_no_primeiro_erro_semantico(self):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(
                'tom 0;\nemitir ausente;\nemitir "😀";'
            )
        self.assertEqual((contexto.exception.linha,
                          contexto.exception.coluna), (1, 5))
        self.assertIn("tom", contexto.exception.detalhe)

    def test_comando_anterior_valido_nao_impede_o_erro_seguinte(self):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(
                'mensagem a = "A";\nemitir a;\nemitir "😀";'
            )
        self.assertEqual((contexto.exception.linha,
                          contexto.exception.coluna), (3, 9))

    def test_erro_semantico_em_comando_posterior(self):
        with self.assertRaises(ErroSemantico) as contexto:
            analisar_fonte(
                'tom 700;\nvelocidade 18;\nemitir "SOS";\nemitir ausente;'
            )
        self.assertEqual((contexto.exception.linha,
                          contexto.exception.coluna), (4, 8))

    def test_parser_ainda_rejeita_erros_estruturais(self):
        with self.assertRaises(ErroSintatico):
            analisar_fonte('emitir "A"; tom 600;')


class ExemplosInvalidosTest(unittest.TestCase):
    CASOS = {
        "nome_nao_declarado.mf": (3, 8, "não foi declarado"),
        "redefinicao.mf": (3, 1, "já foi declarado"),
        "repeticao_zero.mf": (3, 17, "inteiro positivo"),
        "tom_fora_do_limite.mf": (2, 5, "entre 100 e 20000 Hz"),
        "velocidade_zero.mf": (2, 12, "inteiro positivo"),
        "caractere_sem_morse.mf": (2, 13, "representação em Morse"),
    }

    def test_corpus_semantico_invalido(self):
        caminhos = sorted(SEMANTICOS.glob("*.mf"))
        self.assertGreaterEqual(len(caminhos), len(self.CASOS))
        self.assertEqual({c.name for c in caminhos}, set(self.CASOS))
        for caminho in caminhos:
            with self.subTest(arquivo=caminho.name):
                fonte = caminho.read_text(encoding="utf-8")
                # O léxico e o parser aceitam as entradas; a falha é semântica.
                analisar_sintatico(fonte)
                linha, coluna, trecho = self.CASOS[caminho.name]
                with self.assertRaises(ErroSemantico) as contexto:
                    analisar_fonte(fonte)
                self.assertEqual((contexto.exception.linha,
                                  contexto.exception.coluna), (linha, coluna))
                self.assertIn(trecho, contexto.exception.detalhe)

    def test_exemplos_antigos_com_erro_lexico_ou_sintatico_continuam_rejeitados(self):
        with self.assertRaises(ErroLexico):
            analisar_fonte(
                (EXEMPLOS / "invalidos" / "caractere_invalido.mf")
                .read_text(encoding="utf-8"))
        with self.assertRaises(ErroSintatico):
            analisar_fonte(
                (EXEMPLOS / "invalidos" / "sintaticos" / "sem_ponto_virgula.mf")
                .read_text(encoding="utf-8"))


class CliSemanticaTest(unittest.TestCase):
    def test_programa_valido(self):
        resultado = executar(EXEMPLOS / "ola.mf")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stderr, "")
        self.assertEqual(
            resultado.stdout,
            "Programa semanticamente válido: 1 emissão(ões); "
            "tom 600.0 Hz; velocidade 20 WPM.\n",
        )

    def test_padroes_aparecem_na_saida(self):
        resultado = executar(EXEMPLOS / "eco.mf")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("tom 600 Hz; velocidade 20 WPM", resultado.stdout)

    def test_erro_semantico_nao_imprime_sucesso(self):
        resultado = executar(SEMANTICOS / "tom_fora_do_limite.mf")
        self.assertEqual(resultado.returncode, 1)
        self.assertEqual(resultado.stdout, "")
        self.assertIn("erro semântico: linha 2, coluna 5",
                      resultado.stderr)
        self.assertIn("entre 100 e 20000 Hz", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_erros_lexicos_e_sintaticos_sao_categorizados(self):
        casos = [
            (EXEMPLOS / "invalidos" / "caractere_invalido.mf", "erro léxico"),
            (EXEMPLOS / "invalidos" / "sintaticos" / "sem_ponto_virgula.mf",
             "erro sintático"),
        ]
        for caminho, categoria in casos:
            with self.subTest(caminho=caminho.name):
                resultado = executar(caminho)
                self.assertEqual(resultado.returncode, 1)
                self.assertEqual(resultado.stdout, "")
                self.assertIn(categoria, resultado.stderr)
                self.assertIn("linha", resultado.stderr)
                self.assertIn("coluna", resultado.stderr)
                self.assertNotIn("Traceback", resultado.stderr)

    def test_todos_os_exemplos_invalidos_semanticos_pela_cli(self):
        for nome in ExemplosInvalidosTest.CASOS:
            with self.subTest(arquivo=nome):
                resultado = executar(SEMANTICOS / nome)
                self.assertEqual(resultado.returncode, 1)
                self.assertEqual(resultado.stdout, "")
                self.assertIn("erro semântico:", resultado.stderr)

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
        self.assertIn("Valida semanticamente", resultado.stdout)

    def test_execucao_como_modulo(self):
        for modulo in ("src.semantico", "src.analise_semantica"):
            with self.subTest(modulo=modulo):
                resultado = executar_modulo(modulo, "exemplos/ola.mf")
                self.assertEqual(resultado.returncode, 0, resultado.stderr)
                self.assertIn("Programa semanticamente válido",
                              resultado.stdout)

    def test_execucao_fora_do_projeto(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text('emitir "SOS";', encoding="utf-8")
            resultado = executar(fonte, cwd=pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertIn("tom 600 Hz; velocidade 20 WPM", resultado.stdout)

    def test_cli_nao_gera_arquivos_de_saida(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text(
                'mensagem a = "SOS"; emitir a * 2;', encoding="utf-8")
            resultado = executar(fonte, cwd=pasta)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertEqual(
                sorted(p.name for p in Path(pasta).iterdir()), ["entrada.mf"])

    def test_main_recebe_saidas_injetadas(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text('tom 700; emitir "SOS";', encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            retorno = main([str(fonte)], stdout=stdout, stderr=stderr)
            self.assertEqual(retorno, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(
                stdout.getvalue(),
                "Programa semanticamente válido: 1 emissão(ões); "
                "tom 700 Hz; velocidade 20 WPM.\n",
            )

    def test_main_com_erro_semantico_em_saidas_injetadas(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / "entrada.mf"
            fonte.write_text('emitir "😀";', encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            retorno = main([str(fonte)], stdout=stdout, stderr=stderr)
            self.assertEqual(retorno, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("erro semântico:", stderr.getvalue())

    def test_main_com_arquivo_inexistente_em_saidas_injetadas(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        retorno = main(["/caminho/que/nao/existe.mf"],
                       stdout=stdout, stderr=stderr)
        self.assertEqual(retorno, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("não foi possível ler", stderr.getvalue())

    def test_analisar_nao_escreve_nas_saidas_padrao(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            resultado = analisar_fonte('emitir "SOS";')
        self.assertIsInstance(resultado, ResultadoSemantico)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
