import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

from antlr4 import CommonTokenStream, InputStream

from gerado.MorseLang import MorseLang


ROOT = Path(__file__).resolve().parent.parent
GRAMATICA_PARSER = """parser grammar MorseLangParser;
options { tokenVocab=MorseLang; }
programa: (declaracao | configuracao | emissao)* EOF;
declaracao: MENSAGEM IDENT IGUAL expressao PONTO_VIRGULA;
configuracao: TOM (REAL | INTEIRO) PONTO_VIRGULA
            | VELOCIDADE INTEIRO PONTO_VIRGULA;
emissao: EMITIR expressao PONTO_VIRGULA;
expressao: termo (MAIS termo)*;
termo: atomo (VEZES INTEIRO)*;
atomo: TEXTO | IDENT | ABRE_PAR expressao FECHA_PAR;
"""


class ViabilidadeE3Test(unittest.TestCase):
    def test_lexer_pode_alimentar_parser_antlr(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte_parser = Path(pasta) / "MorseLangParser.g4"
            fonte_parser.write_text(GRAMATICA_PARSER, encoding="utf-8")

            resultado = subprocess.run(
                ["java", "-jar", str(ROOT / "tools" / "antlr-4.13.2-complete.jar"),
                 "-Dlanguage=Python3", "-lib", str(ROOT / "gerado"),
                 "-o", pasta, str(fonte_parser)],
                capture_output=True, text=True,
            )
            self.assertEqual(resultado.returncode, 0, resultado.stderr)

            modulo = importlib.util.spec_from_file_location(
                "MorseLangParser", Path(pasta) / "MorseLangParser.py"
            )
            self.assertIsNotNone(modulo)
            parser_gerado = importlib.util.module_from_spec(modulo)
            modulo.loader.exec_module(parser_gerado)

            for nome in ("ola.mf", "eco.mf", "aviso.mf"):
                with self.subTest(nome=nome):
                    fonte = (ROOT / "exemplos" / nome).read_text(encoding="utf-8")
                    tokens = CommonTokenStream(MorseLang(InputStream(fonte)))
                    parser = parser_gerado.MorseLangParser(tokens)
                    parser.programa()
                    self.assertEqual(parser.getNumberOfSyntaxErrors(), 0)


if __name__ == "__main__":
    unittest.main()
