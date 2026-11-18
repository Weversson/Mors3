import io
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path
import tempfile
import wave

from src.execucao import Timeline
from src.geracao import (
    ErroGeracao,
    escrever_morse,
    escrever_wav,
    gerar_morse,
    gerar_pcm,
    gerar_wav,
    morse_de_texto,
)
from src.semantico import analisar_fonte
from src.execucao import expandir

RAIZ = Path(__file__).resolve().parent.parent


def timeline_de(fonte: str) -> Timeline:
    return expandir(analisar_fonte(fonte))


class TextoTest(unittest.TestCase):
    def test_morse_de_texto(self):
        self.assertEqual(
            morse_de_texto("SOS 123"),
            "... --- ... / .---- ..--- ...--",
        )

    def test_acentos_sao_normalizados(self):
        self.assertEqual(morse_de_texto("AÇÃO"), ".- -.-. .- ---")

    def test_texto_vazio(self):
        self.assertEqual(morse_de_texto(""), "")

    def test_uma_linha_por_emissao(self):
        timeline = timeline_de('emitir "SOS"; emitir "A 1";')
        self.assertEqual(
            gerar_morse(timeline),
            "... --- ...\n.- / .----\n",
        )

    def test_emissao_vazia_gera_linha_vazia(self):
        self.assertEqual(gerar_morse(timeline_de('emitir "";')), "\n")

    def test_caractere_sem_morse(self):
        timeline = Timeline(
            Decimal("600"), Decimal("20"), Decimal("60"),
            ("😀",), "😀", (),
        )
        with self.assertRaises(ErroGeracao):
            gerar_morse(timeline)

    def test_tipos_invalidos(self):
        with self.assertRaises(TypeError):
            morse_de_texto(123)
        with self.assertRaises(TypeError):
            gerar_morse("não é timeline")

    def test_escrever_morse(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = escrever_morse(
                timeline_de('emitir "E";'), Path(diretorio) / "saida.morse")
            self.assertEqual(caminho.read_text(encoding="utf-8"), ".\n")


class AudioTest(unittest.TestCase):
    def test_cabecalho_wav(self):
        dados = gerar_wav(
            timeline_de('emitir "E";'), taxa_amostragem=8000)
        with wave.open(io.BytesIO(dados)) as arquivo:
            self.assertEqual(arquivo.getnchannels(), 1)
            self.assertEqual(arquivo.getsampwidth(), 2)
            self.assertEqual(arquivo.getframerate(), 8000)
            # Um ponto a 20 WPM dura 60 ms: 480 amostras a 8 kHz.
            self.assertEqual(arquivo.getnframes(), 480)

    def test_timeline_vazia_gera_wav_valido(self):
        dados = gerar_wav(timeline_de('emitir "";'))
        with wave.open(io.BytesIO(dados)) as arquivo:
            self.assertEqual(arquivo.getnframes(), 0)

    def test_frequencia_do_tom(self):
        timeline = timeline_de('tom 600; velocidade 1; emitir "E";')
        amostras = gerar_pcm(timeline, taxa_amostragem=8000)
        anterior = 0
        cruzamentos = 0
        for valor in amostras:
            if valor == 0:
                continue
            sinal = 1 if valor > 0 else -1
            if anterior != 0 and sinal != anterior:
                cruzamentos += 1
            anterior = sinal
        # 600 Hz durante 1,2 s produz aproximadamente 1440 cruzamentos.
        self.assertGreater(cruzamentos, 1400)
        self.assertLess(cruzamentos, 1480)

    def test_silencio_entre_caracteres(self):
        timeline = timeline_de('emitir "E E";')
        amostras = gerar_pcm(timeline, taxa_amostragem=8000)
        self.assertEqual(amostras[0], 0)
        self.assertTrue(any(valor != 0 for valor in amostras[:480]))
        self.assertTrue(all(valor == 0 for valor in amostras[480:660]))
        self.assertTrue(any(valor != 0 for valor in amostras[660:]))

    def test_amplitude_limitada(self):
        amostras = gerar_pcm(timeline_de('emitir "T";'))
        self.assertTrue(any(valor != 0 for valor in amostras))
        self.assertLessEqual(max(amostras), 32767)
        self.assertGreaterEqual(min(amostras), -32767)

    def test_opcoes_invalidas(self):
        timeline = timeline_de('emitir "E";')
        casos = (
            {"taxa_amostragem": 0},
            {"taxa_amostragem": True},
            {"amplitude": 0},
            {"amplitude": 1.1},
            {"amplitude": float("nan")},
            {"rampa_ms": -1},
        )
        for opcoes in casos:
            with self.subTest(opcoes=opcoes):
                with self.assertRaises(ValueError):
                    gerar_wav(timeline, **opcoes)

    def test_tipo_invalido(self):
        with self.assertRaises(TypeError):
            gerar_pcm("não é timeline")

    def test_escrever_wav(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = escrever_wav(
                timeline_de('emitir "E";'),
                Path(diretorio) / "saida.wav",
                taxa_amostragem=8000,
            )
            self.assertEqual(caminho.read_bytes()[:4], b"RIFF")


class CliTest(unittest.TestCase):
    def executar(self, *argumentos):
        return subprocess.run(
            [sys.executable, "-m", "src.geracao", *argumentos],
            cwd=RAIZ, capture_output=True, text=True,
        )

    def test_cli_gera_os_dois_arquivos(self):
        with tempfile.TemporaryDirectory() as diretorio:
            entrada = Path(diretorio) / "programa.mf"
            entrada.write_text('emitir "E";', encoding="utf-8")
            morse = Path(diretorio) / "customizado.morse"
            wav = Path(diretorio) / "customizado.wav"
            processo = self.executar(
                str(entrada), "--morse", str(morse), "--wav", str(wav))
            self.assertEqual(processo.returncode, 0, processo.stderr)
            self.assertIn("gerado", processo.stdout)
            self.assertEqual(morse.read_text(encoding="utf-8"), ".\n")
            self.assertEqual(wav.read_bytes()[:4], b"RIFF")

    def test_cli_caminhos_padrao(self):
        with tempfile.TemporaryDirectory() as diretorio:
            entrada = Path(diretorio) / "programa.mf"
            entrada.write_text('emitir "E";', encoding="utf-8")
            processo = self.executar(str(entrada))
            self.assertEqual(processo.returncode, 0, processo.stderr)
            self.assertTrue((Path(diretorio) / "programa.morse").is_file())
            self.assertTrue((Path(diretorio) / "programa.wav").is_file())

    def test_cli_apenas_morse(self):
        with tempfile.TemporaryDirectory() as diretorio:
            entrada = Path(diretorio) / "programa.mf"
            entrada.write_text('emitir "E";', encoding="utf-8")
            morse = Path(diretorio) / "so.morse"
            processo = self.executar(str(entrada), "--morse", str(morse))
            self.assertEqual(processo.returncode, 0, processo.stderr)
            self.assertTrue(morse.is_file())
            self.assertFalse((Path(diretorio) / "programa.wav").exists())

    def test_cli_erro_semantico(self):
        with tempfile.TemporaryDirectory() as diretorio:
            entrada = Path(diretorio) / "invalido.mf"
            entrada.write_text("emitir ausente;", encoding="utf-8")
            processo = self.executar(str(entrada))
            self.assertEqual(processo.returncode, 1)
            self.assertIn("erro:", processo.stderr)
            self.assertFalse((Path(diretorio) / "invalido.morse").exists())

    def test_cli_opcoes_invalidas(self):
        processo = self.executar(
            str(RAIZ / "exemplos" / "ola.mf"), "--limite", "-1")
        self.assertEqual(processo.returncode, 2)


if __name__ == "__main__":
    unittest.main()
