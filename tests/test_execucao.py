import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from io import StringIO
from pathlib import Path

from src.analise_semantica.modelo import ResultadoSemantico
from src.ast_morselang import Emissao, Programa, Texto
from src.execucao import (
    Evento, ErroExecucao, Timeline, expandir, expandir_texto, unidade_ms,
)
from src.execucao.__main__ import main as main_execucao
from src.semantico import analisar_fonte

RAIZ = Path(__file__).resolve().parent.parent


def timeline_de(fonte: str, **kwargs) -> Timeline:
    return expandir(analisar_fonte(fonte), **kwargs)


def resultado_manual(expressao, tom="600", velocidade="20") -> ResultadoSemantico:
    programa = Programa(1, 1, (Emissao(1, 8, expressao),))
    return ResultadoSemantico(
        programa=programa,
        tom=Decimal(tom),
        velocidade=Decimal(velocidade),
        mensagens=(),
        emissoes=programa.comandos,
    )


class UnidadeTest(unittest.TestCase):
    def test_padroes_da_linguagem(self):
        timeline = timeline_de('emitir "A";')
        self.assertEqual(timeline.tom, Decimal("600"))
        self.assertEqual(timeline.velocidade, Decimal("20"))
        self.assertEqual(timeline.unidade_ms, Decimal("60"))

    def test_configuracoes_efetivas(self):
        timeline = timeline_de('tom 700; velocidade 12; emitir "A";')
        self.assertEqual(timeline.tom, Decimal("700"))
        self.assertEqual(timeline.velocidade, Decimal("12"))
        self.assertEqual(timeline.unidade_ms, Decimal("100"))

    def test_velocidade_que_nao_divide_exatamente(self):
        self.assertEqual(
            unidade_ms(Decimal("7")),
            Decimal("1200") / Decimal("7"),
        )

    def test_velocidade_invalida(self):
        for valor in (Decimal("0"), Decimal("-1")):
            with self.subTest(valor=valor):
                with self.assertRaises(ErroExecucao):
                    unidade_ms(valor)

    def test_velocidade_nao_numerica(self):
        with self.assertRaises(ErroExecucao):
            unidade_ms("rápido")


class ExpansaoTest(unittest.TestCase):
    def test_texto_literal(self):
        self.assertEqual(timeline_de('emitir "SOS";').texto, "SOS")

    def test_concatenacao_nao_insere_espaco(self):
        self.assertEqual(timeline_de('emitir "A" + "B";').texto, "AB")

    def test_repeticao(self):
        self.assertEqual(timeline_de('emitir "A" * 3;').texto, "AAA")

    def test_referencia_resolve_declaracao(self):
        timeline = timeline_de('mensagem a = "A"; emitir a;')
        self.assertEqual(timeline.texto, "A")

    def test_referencia_composta(self):
        timeline = timeline_de(
            'mensagem a = "A"; mensagem b = a + "B"; emitir b;')
        self.assertEqual(timeline.texto, "AB")

    def test_repeticao_de_referencia(self):
        timeline = timeline_de('mensagem a = "A"; emitir a * 2;')
        self.assertEqual(timeline.texto, "AA")

    def test_espacos_sao_normalizados(self):
        timeline = timeline_de('emitir "  A   B  ";')
        self.assertEqual(timeline.texto, "A B")
        self.assertEqual(timeline.textos, ("A B",))

    def test_emissoes_sao_separadas_por_espaco(self):
        timeline = timeline_de('emitir "A"; emitir "B";')
        self.assertEqual(timeline.textos, ("A", "B"))
        self.assertEqual(timeline.texto, "A B")

    def test_emissao_vazia_nao_cria_espaco_extra(self):
        timeline = timeline_de('emitir "A"; emitir ""; emitir "B";')
        self.assertEqual(timeline.textos, ("A", "", "B"))
        self.assertEqual(timeline.texto, "A B")
        self.assertEqual(timeline.quantidade_emissoes, 3)

    def test_texto_vazio_nao_produz_eventos(self):
        timeline = timeline_de('emitir "";')
        self.assertEqual(timeline.eventos, ())
        self.assertEqual(timeline.duracao_total_ms, Decimal(0))

    def test_texto_com_apenas_espacos_nao_produz_eventos(self):
        timeline = timeline_de('emitir "   ";')
        self.assertEqual(timeline.texto, "")
        self.assertEqual(timeline.eventos, ())

    def test_acentos_preservados_no_texto(self):
        timeline = timeline_de('emitir "Ação";')
        self.assertEqual(timeline.texto, "Ação")

    def test_expandir_texto_publico(self):
        resultado = analisar_fonte('mensagem a = "A"; emitir a + "B";')
        self.assertEqual(
            expandir_texto(
                resultado.emissoes[0].expressao, resultado.mensagens),
            "AB",
        )

    def test_expressao_desconhecida(self):
        with self.assertRaises(TypeError):
            expandir_texto(object())


class DuracaoTest(unittest.TestCase):
    def test_sos_completo(self):
        timeline = timeline_de('emitir "SOS";')
        # S = 3 pontos; O = 3 traços; S = 3 pontos, com os silêncios PARIS.
        self.assertEqual(timeline.duracao_total_ms, Decimal("1620"))
        self.assertEqual(timeline.quantidade_eventos, 17)

    def test_espaco_entre_palavras(self):
        timeline = timeline_de('emitir "A B";')
        self.assertEqual(timeline.duracao_total_ms, Decimal("1260"))
        silencio = timeline.eventos[3]
        self.assertEqual(silencio.tipo, "silencio")
        self.assertEqual(silencio.motivo, "palavra")
        self.assertEqual(silencio.duracao_ms, Decimal("420"))

    def test_espaco_entre_emissoes(self):
        timeline = timeline_de('emitir "A"; emitir "B";')
        self.assertEqual(timeline.duracao_total_ms, Decimal("1260"))
        silencio = timeline.eventos[3]
        self.assertEqual(silencio.motivo, "emissao")
        self.assertEqual(silencio.duracao_ms, Decimal("420"))

    def test_concatenacao_usa_intervalo_entre_caracteres(self):
        timeline = timeline_de('emitir "A" + "B";')
        self.assertEqual(timeline.duracao_total_ms, Decimal("1020"))
        self.assertEqual(timeline.eventos[3].motivo, "caractere")
        self.assertEqual(timeline.eventos[3].duracao_ms, Decimal("180"))

    def test_repeticao_concatenada(self):
        timeline = timeline_de('emitir ("A" + "B") * 2;')
        self.assertEqual(timeline.duracao_total_ms, Decimal("2220"))

    def test_repeticao_com_zeros_a_esquerda(self):
        timeline = timeline_de('emitir "A" * 007;')
        self.assertEqual(timeline.texto, "A" * 7)
        self.assertEqual(timeline.duracao_total_ms, Decimal("3180"))

    def test_acentos_usam_codigo_normalizado(self):
        timeline = timeline_de('emitir "Ação";')
        self.assertEqual(timeline.duracao_total_ms, Decimal("2460"))
        self.assertEqual(
            sum(evento.tipo == "tom" for evento in timeline.eventos), 11)

    def test_eventos_sao_contiguos_e_positivos(self):
        timeline = timeline_de('emitir "SOS";')
        for atual, proximo in zip(timeline.eventos, timeline.eventos[1:]):
            self.assertEqual(atual.fim_ms, proximo.inicio_ms)
        for evento in timeline.eventos:
            self.assertGreater(evento.duracao_ms, 0)
        self.assertEqual(timeline.eventos[0].inicio_ms, Decimal(0))
        self.assertEqual(
            timeline.eventos[-1].fim_ms, timeline.duracao_total_ms)

    def test_tons_e_silencios_tem_simbolos_coerentes(self):
        for evento in timeline_de('emitir "SOS";').eventos:
            if evento.tipo == "tom":
                self.assertIn(evento.simbolo, {".", "-"})
            else:
                self.assertIsNone(evento.simbolo)
                self.assertIn(
                    evento.motivo, {"simbolo", "caractere", "palavra", "emissao"})


class ErroExecucaoTest(unittest.TestCase):
    def test_caractere_sem_morse(self):
        with self.assertRaises(ErroExecucao) as contexto:
            expandir(resultado_manual(Texto(1, 15, "A😀")))
        self.assertIn("não possui representação em Morse",
                      str(contexto.exception))

    def test_velocidade_zero(self):
        with self.assertRaises(ErroExecucao):
            expandir(resultado_manual(Texto(1, 15, "A"), velocidade="0"))

    def test_tipo_incorreto(self):
        with self.assertRaises(TypeError):
            expandir(object())

    def test_limite_de_caracteres(self):
        with self.assertRaises(ErroExecucao):
            timeline_de('emitir "ABCDE";', limite_caracteres=4)

    def test_limite_aceita_exatamente_o_tamanho(self):
        timeline = timeline_de('emitir "ABCDE";', limite_caracteres=5)
        self.assertEqual(timeline.texto, "ABCDE")

    def test_limite_em_repeticao_nao_materializa_o_texto(self):
        with self.assertRaises(ErroExecucao):
            timeline_de('emitir "AB" * 1000000;', limite_caracteres=100)

    def test_limite_em_referencia_repetida(self):
        with self.assertRaises(ErroExecucao):
            timeline_de(
                'mensagem a = "AB" * 1000; emitir a;',
                limite_caracteres=100,
            )


class ModeloTest(unittest.TestCase):
    def test_evento_tom_requer_simbolo(self):
        with self.assertRaises(ValueError):
            Evento("tom", Decimal(0), Decimal(60))

    def test_evento_silencio_nao_aceita_simbolo(self):
        with self.assertRaises(ValueError):
            Evento(
                "silencio", Decimal(0), Decimal(60), simbolo=".",
                motivo="palavra")

    def test_tipo_de_evento_desconhecido(self):
        with self.assertRaises(ValueError):
            Evento("ruido", Decimal(0), Decimal(60))

    def test_duracao_negativa(self):
        with self.assertRaises(ValueError):
            Evento(
                "silencio", Decimal(0), Decimal(-1), motivo="palavra")


class ParaDictTest(unittest.TestCase):
    def test_estrutura_json(self):
        timeline = timeline_de('emitir "SOS";')
        dados = timeline.para_dict()
        self.assertEqual(dados["tom"], "600")
        self.assertEqual(dados["velocidade"], "20")
        self.assertEqual(dados["unidade_ms"], "60")
        self.assertEqual(dados["texto"], "SOS")
        self.assertEqual(dados["quantidade_eventos"], 17)
        self.assertEqual(dados["quantidade_emissoes"], 1)
        self.assertEqual(dados["duracao_total_ms"], "1620")
        primeiro = dados["eventos"][0]
        self.assertEqual(primeiro["tipo"], "tom")
        self.assertEqual(primeiro["simbolo"], ".")
        self.assertEqual(primeiro["inicio_ms"], "0")
        self.assertEqual(primeiro["duracao_ms"], "60")
        self.assertEqual(primeiro["fim_ms"], "60")
        json.dumps(dados)

    def test_decimal_nao_usa_notacao_cientifica(self):
        timeline = timeline_de('velocidade 7; emitir "A";')
        dados = timeline.para_dict()
        self.assertNotIn("E", dados["unidade_ms"])
        self.assertNotIn("e", dados["unidade_ms"])


class ExemplosTest(unittest.TestCase):
    def test_todos_os_exemplos_validos_expandem(self):
        exemplos = sorted((RAIZ / "exemplos").glob("*.mf"))
        self.assertTrue(exemplos)
        for caminho in exemplos:
            with self.subTest(exemplo=caminho.name):
                timeline = expandir(
                    analisar_fonte(caminho.read_text(encoding="utf-8")))
                self.assertIsInstance(timeline, Timeline)
                self.assertGreater(timeline.quantidade_eventos, 0)


class CliTest(unittest.TestCase):
    def _executar(self, *argumentos):
        saida, erro = StringIO(), StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            codigo = main_execucao(list(argumentos))
        return codigo, saida.getvalue(), erro.getvalue()

    def test_json_completo(self):
        codigo, saida, erro = self._executar(
            str(RAIZ / "exemplos" / "ola.mf"))
        self.assertEqual(codigo, 0)
        self.assertEqual(erro, "")
        dados = json.loads(saida)
        self.assertIn("eventos", dados)
        self.assertGreater(dados["quantidade_eventos"], 0)

    def test_resumo(self):
        codigo, saida, _ = self._executar(
            str(RAIZ / "exemplos" / "ola.mf"), "--resumo")
        self.assertEqual(codigo, 0)
        self.assertIn("emissão(ões)", saida)
        self.assertIn("evento(s)", saida)

    def test_arquivo_inexistente(self):
        codigo, _, erro = self._executar("/caminho/que/nao/existe.mf")
        self.assertEqual(codigo, 1)
        self.assertIn("não foi possível ler", erro)

    def test_erro_semantico(self):
        caminho = (RAIZ / "exemplos" / "invalidos" / "semanticos"
                   / "nome_nao_declarado.mf")
        codigo, _, erro = self._executar(str(caminho))
        self.assertEqual(codigo, 1)
        self.assertIn("erro semântico:", erro)

    def test_limite_excedido(self):
        codigo, _, erro = self._executar(
            str(RAIZ / "exemplos" / "ola.mf"), "--limite", "1")
        self.assertEqual(codigo, 1)
        self.assertIn("erro de execução:", erro)

    def test_limite_negativo_e_uso_incorreto(self):
        with self.assertRaises(SystemExit) as contexto:
            self._executar(
                str(RAIZ / "exemplos" / "ola.mf"), "--limite", "-1")
        self.assertEqual(contexto.exception.code, 2)

    def test_execucao_como_modulo(self):
        processo = subprocess.run(
            [sys.executable, "-m", "src.execucao",
             str(RAIZ / "exemplos" / "ola.mf"), "--resumo"],
            cwd=RAIZ, capture_output=True, text=True,
        )
        self.assertEqual(processo.returncode, 0, processo.stderr)
        self.assertIn("evento(s)", processo.stdout)


if __name__ == "__main__":
    unittest.main()
