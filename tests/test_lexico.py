import subprocess
import sys
import unittest
from pathlib import Path

from src.lexico import ErroLexico, analisar


ROOT = Path(__file__).resolve().parent.parent
EXEMPLOS = ROOT / "exemplos"


def executar(caminho: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "lexico.py"), str(caminho)],
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


class TokensTest(unittest.TestCase):
    def test_categorias_e_posicoes(self):
        tokens = analisar('mensagem nome = "OI";\ntom 600.5; velocidade 20; emitir nome * 2;')
        self.assertEqual(
            [t.tipo for t in tokens],
            ["MENSAGEM", "IDENT", "IGUAL", "TEXTO", "PONTO_VIRGULA",
             "TOM", "REAL", "PONTO_VIRGULA", "VELOCIDADE", "INTEIRO",
             "PONTO_VIRGULA", "EMITIR", "IDENT", "VEZES", "INTEIRO",
             "PONTO_VIRGULA"],
        )
        self.assertEqual((tokens[0].linha, tokens[0].coluna), (1, 1))
        self.assertEqual((tokens[5].linha, tokens[5].coluna), (2, 1))
        self.assertEqual(tokens[6].texto, "600.5")

    def test_comentarios_e_espacos_descartados(self):
        tokens = analisar('// ignorado\n  emitir "//"; // ignorado\n')
        self.assertEqual([t.tipo for t in tokens], ["EMITIR", "TEXTO", "PONTO_VIRGULA"])
        self.assertEqual((tokens[0].linha, tokens[0].coluna), (2, 3))
        self.assertEqual(tokens[1].texto, '"//"')

    def test_palavra_chave_nao_engole_identificador(self):
        tokens = analisar("mensagem mensagem_extra = \"A\";")
        self.assertEqual([t.tipo for t in tokens[:2]], ["MENSAGEM", "IDENT"])

    def test_erro_lexico_expõe_linha_e_coluna(self):
        with self.assertRaises(ErroLexico) as erro:
            analisar('emitir "OK";\n  @')
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))


class ExemplosTest(unittest.TestCase):
    def test_tres_validos(self):
        for nome in ("ola.mf", "eco.mf", "aviso.mf"):
            with self.subTest(nome=nome):
                resultado = executar(EXEMPLOS / nome)
                self.assertEqual(resultado.returncode, 0, resultado.stderr)
                self.assertIn("tokens reconhecidos", resultado.stdout)
                self.assertNotIn("COMENTARIO", resultado.stdout)
                self.assertNotIn("ESPACO", resultado.stdout)

    def test_tres_invalidos_com_posicao(self):
        invalidos = {
            "caractere_invalido.mf": (1, 14),
            "texto_sem_fechar.mf": (1, 8),
            "numero_malformado.mf": (1, 8),
        }
        for nome, (linha, coluna) in invalidos.items():
            with self.subTest(nome=nome):
                resultado = executar(EXEMPLOS / "invalidos" / nome)
                self.assertEqual(resultado.returncode, 1)
                self.assertIn(f"linha {linha}, coluna {coluna}", resultado.stderr)
                self.assertNotIn("tokens reconhecidos", resultado.stdout)


if __name__ == "__main__":
    unittest.main()
