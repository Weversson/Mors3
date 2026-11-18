import http.client
import json
import threading
import unittest
import urllib.error
import urllib.request

from src.visual import LIMITE_PADRAO, analisar, criar_servidor
from src.visual.servidor import LIMITE_CORPO


class ApiTest(unittest.TestCase):
    def test_programa_valido(self):
        dados = analisar('emitir "SOS";')
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["tom"], "600")
        self.assertEqual(dados["velocidade"], "20")
        self.assertEqual(dados["ast"]["tipo"], "Programa")
        self.assertEqual(dados["timeline"]["texto"], "SOS")
        self.assertEqual(dados["timeline"]["quantidade_eventos"], 17)
        self.assertEqual(dados["simbolos"], [])
        self.assertTrue(dados["tokens"])

    def test_tokens_preservam_tipo_e_posicao(self):
        dados = analisar('emitir "A";')
        primeiro = dados["tokens"][0]
        self.assertEqual(primeiro["tipo"], "EMITIR")
        self.assertEqual(primeiro["texto"], "emitir")
        self.assertEqual((primeiro["linha"], primeiro["coluna"]), (1, 1))

    def test_simbolos_declarados(self):
        dados = analisar('mensagem a = "A"; emitir a;')
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["simbolos"], [
            {"nome": "a", "linha": 1, "coluna": 1},
        ])

    def test_erro_lexico(self):
        dados = analisar('emitir "A" ?;')
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "lexico")
        self.assertIsNone(dados["ast"])
        self.assertEqual([t["tipo"] for t in dados["tokens"]],
                         ["EMITIR", "TEXTO"])
        self.assertIn("linha", dados)
        self.assertIn("coluna", dados)

    def test_erro_sintatico(self):
        dados = analisar('emitir "A"')
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "sintatico")
        self.assertIsNone(dados["ast"])
        self.assertTrue(dados["tokens"])

    def test_erro_semantico_mantem_ast(self):
        dados = analisar('emitir ausente;')
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "semantico")
        self.assertEqual(dados["ast"]["tipo"], "Programa")
        self.assertEqual((dados["linha"], dados["coluna"]), (1, 8))
        self.assertIn("não foi declarado", dados["detalhe"])
        self.assertNotIn("timeline", dados)

    def test_erro_execucao(self):
        dados = analisar('emitir "A" * 1000;', limite_caracteres=10)
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "execucao")
        self.assertIsNotNone(dados["ast"])
        self.assertNotIn("timeline", dados)

    def test_limite_none(self):
        dados = analisar('emitir "A";', limite_caracteres=None)
        self.assertTrue(dados["ok"])

    def test_limite_invalido(self):
        for limite in (-1, True, "10", 1.5):
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    analisar('emitir "A";', limite_caracteres=limite)

    def test_fonte_precisa_ser_str(self):
        with self.assertRaises(TypeError):
            analisar(b'emitir "A";')

    def test_texto_vazio(self):
        dados = analisar('emitir "";')
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["timeline"]["eventos"], [])
        self.assertEqual(dados["timeline"]["duracao_total_ms"], "0")

    def test_resposta_serializavel(self):
        json.dumps(analisar('mensagem a = "A"; emitir a;'))
        json.dumps(analisar('emitir ausente;'))

    def test_limite_padrao_exportado(self):
        self.assertEqual(LIMITE_PADRAO, 10_000)


class ServidorTest(unittest.TestCase):
    LIMITE = 64

    @classmethod
    def setUpClass(cls):
        cls.servidor = criar_servidor(
            "127.0.0.1", 0, limite_caracteres=cls.LIMITE)
        cls.thread = threading.Thread(
            target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()
        cls.host, cls.porta = cls.servidor.server_address[:2]
        cls.base = f"http://{cls.host}:{cls.porta}"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.thread.join(timeout=5)

    def requisitar(
        self,
        caminho,
        *,
        metodo="GET",
        dados=None,
        corpo=None,
        cabecalhos=None,
    ):
        cabecalhos = dict(cabecalhos or {})
        if dados is not None:
            corpo = json.dumps(dados).encode("utf-8")
            cabecalhos.setdefault("Content-Type", "application/json")
        requisicao = urllib.request.Request(
            self.base + caminho,
            data=corpo,
            headers=cabecalhos,
            method=metodo,
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=5) as resposta:
                return resposta.status, dict(resposta.headers), resposta.read()
        except urllib.error.HTTPError as erro:
            try:
                return erro.code, dict(erro.headers), erro.read()
            finally:
                erro.close()

    def json_de(self, resposta):
        return json.loads(resposta[2].decode("utf-8"))

    def test_saude(self):
        status, cabecalhos, corpo = self.requisitar("/api/saude")
        self.assertEqual(status, 200)
        self.assertTrue(cabecalhos["Content-Type"].startswith("application/json"))
        dados = json.loads(corpo)
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["api"], "/api/analisar")
        self.assertEqual(dados["limite_caracteres"], self.LIMITE)

    def test_alias_health(self):
        status, _, corpo = self.requisitar("/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(corpo)["ok"])

    def test_pagina_inicial(self):
        status, cabecalhos, corpo = self.requisitar("/")
        self.assertEqual(status, 200)
        self.assertTrue(cabecalhos["Content-Type"].startswith("text/html"))
        texto = corpo.decode("utf-8")
        self.assertIn("MorseLang", texto)
        self.assertIn("/app.js", texto)

    def test_arquivos_estaticos(self):
        for caminho, tipo in (
            ("/estilo.css", "text/css"),
            ("/app.js", "text/javascript"),
            ("/favicon.svg", "image/svg+xml"),
        ):
            with self.subTest(caminho=caminho):
                status, cabecalhos, corpo = self.requisitar(caminho)
                self.assertEqual(status, 200)
                self.assertTrue(cabecalhos["Content-Type"].startswith(tipo))
                self.assertTrue(corpo)

    def test_head_sem_corpo(self):
        status, cabecalhos, corpo = self.requisitar("/", metodo="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(corpo, b"")
        self.assertGreater(int(cabecalhos["Content-Length"]), 0)

    def test_pagina_inclui_controles_de_reproducao(self):
        _, _, corpo = self.requisitar("/")
        texto = corpo.decode("utf-8")
        for marcador in (
            "botao-reproduzir",
            "botao-reiniciar",
            "volume",
            "evento-atual",
        ):
            with self.subTest(marcador=marcador):
                self.assertIn(marcador, texto)

    def test_script_usa_web_audio_e_api(self):
        _, _, corpo = self.requisitar("/app.js")
        texto = corpo.decode("utf-8")
        self.assertIn("AudioContext", texto)
        self.assertIn("/api/analisar", texto)
        self.assertIn("requestAnimationFrame", texto)

    def test_pagina_inclui_botoes_de_download(self):
        _, _, corpo = self.requisitar("/")
        texto = corpo.decode("utf-8")
        self.assertIn("baixar-morse", texto)
        self.assertIn("baixar-wav", texto)

    def test_script_usa_rota_de_exportacao(self):
        _, _, corpo = self.requisitar("/app.js")
        self.assertIn("/api/exportar", corpo.decode("utf-8"))

    def test_exportar_morse(self):
        status, cabecalhos, corpo = self.requisitar(
            "/api/exportar", metodo="POST",
            dados={"fonte": 'emitir "SOS";', "formato": "morse"})
        self.assertEqual(status, 200)
        self.assertTrue(cabecalhos["Content-Type"].startswith("text/plain"))
        self.assertIn("morselang.morse", cabecalhos["Content-Disposition"])
        self.assertEqual(corpo.decode("utf-8"), "... --- ...\n")

    def test_exportar_wav(self):
        status, cabecalhos, corpo = self.requisitar(
            "/api/exportar", metodo="POST",
            dados={"fonte": 'emitir "E";', "formato": "wav"})
        self.assertEqual(status, 200)
        self.assertEqual(cabecalhos["Content-Type"], "audio/wav")
        self.assertIn("morselang.wav", cabecalhos["Content-Disposition"])
        self.assertEqual(corpo[:4], b"RIFF")

    def test_exportar_formato_invalido(self):
        status, _, corpo = self.requisitar(
            "/api/exportar", metodo="POST",
            dados={"fonte": 'emitir "E";', "formato": "mp3"})
        self.assertEqual(status, 400)
        self.assertEqual("requisicao", json.loads(corpo)["etapa"])

    def test_exportar_erro_semantico(self):
        status, _, corpo = self.requisitar(
            "/api/exportar", metodo="POST",
            dados={"fonte": "emitir ausente;", "formato": "morse"})
        self.assertEqual(status, 200)
        dados = json.loads(corpo)
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "semantico")

    def test_exportar_limite_do_servidor(self):
        dados = self.json_de(self.requisitar(
            "/api/exportar", metodo="POST",
            dados={"fonte": 'emitir "ABCDE";', "formato": "wav",
                   "limite": 3}))
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "execucao")

    def test_get_em_exportar_e_metodo_incorreto(self):
        status, cabecalhos, corpo = self.requisitar("/api/exportar")
        self.assertEqual(status, 405)
        self.assertEqual(cabecalhos["Allow"], "POST")
        self.assertFalse(json.loads(corpo)["ok"])

    def test_analisar_valido(self):
        status, _, corpo = self.requisitar(
            "/api/analisar", metodo="POST", dados={"fonte": 'emitir "SOS";'})
        self.assertEqual(status, 200)
        dados = json.loads(corpo)
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["timeline"]["quantidade_eventos"], 17)

    def test_analisar_erro_semantico(self):
        status, _, corpo = self.requisitar(
            "/api/analisar", metodo="POST", dados={"fonte": "emitir ausente;"})
        self.assertEqual(status, 200)
        dados = json.loads(corpo)
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "semantico")

    def test_analisar_erro_sintatico(self):
        dados = self.json_de(self.requisitar(
            "/api/analisar", metodo="POST", dados={"fonte": 'emitir "A"'}))
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "sintatico")

    def test_analisar_erro_lexico(self):
        dados = self.json_de(self.requisitar(
            "/api/analisar", metodo="POST", dados={"fonte": 'emitir "A" ?;'}))
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "lexico")

    def test_json_invalido(self):
        status, _, corpo = self.requisitar(
            "/api/analisar", metodo="POST", corpo=b"{nao",
            cabecalhos={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(corpo)["etapa"], "requisicao")

    def test_campo_fonte_ausente(self):
        status, _, _ = self.requisitar(
            "/api/analisar", metodo="POST", dados={"outro": 1})
        self.assertEqual(status, 400)

    def test_fonte_nao_e_string(self):
        status, _, _ = self.requisitar(
            "/api/analisar", metodo="POST", dados={"fonte": 42})
        self.assertEqual(status, 400)

    def test_content_type_incorreto(self):
        status, _, _ = self.requisitar(
            "/api/analisar", metodo="POST", corpo=b'{"fonte":"emitir \\"A\\";"}',
            cabecalhos={"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_limite_invalido(self):
        for limite in (-1, True, "10"):
            with self.subTest(limite=limite):
                status, _, _ = self.requisitar(
                    "/api/analisar", metodo="POST",
                    dados={"fonte": 'emitir "A";', "limite": limite})
                self.assertEqual(status, 400)

    def test_limite_do_corpo_e_aplicado(self):
        dados = self.json_de(self.requisitar(
            "/api/analisar", metodo="POST",
            dados={"fonte": 'emitir "A" * 100;', "limite": 1000}))
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "execucao")

    def test_limite_menor_que_o_servidor(self):
        dados = self.json_de(self.requisitar(
            "/api/analisar", metodo="POST",
            dados={"fonte": 'emitir "ABCDE";', "limite": 3}))
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["etapa"], "execucao")

    def test_get_em_analisar_e_metodo_incorreto(self):
        status, cabecalhos, corpo = self.requisitar("/api/analisar")
        self.assertEqual(status, 405)
        self.assertEqual(cabecalhos["Allow"], "POST")
        self.assertFalse(json.loads(corpo)["ok"])

    def test_rotas_inexistentes(self):
        for caminho in ("/api/nao-existe", "/arquivo-inexistente"):
            with self.subTest(caminho=caminho):
                status, _, _ = self.requisitar(caminho)
                self.assertEqual(status, 404)

    def test_tentativa_de_sair_do_diretorio_web(self):
        conexao = http.client.HTTPConnection(self.host, self.porta, timeout=5)
        try:
            conexao.request("GET", "/../README.md")
            resposta = conexao.getresponse()
            self.assertEqual(resposta.status, 404)
            resposta.read()
        finally:
            conexao.close()

    def test_corpo_grande(self):
        conexao = http.client.HTTPConnection(self.host, self.porta, timeout=5)
        try:
            conexao.putrequest("POST", "/api/analisar")
            conexao.putheader("Content-Type", "application/json")
            conexao.putheader("Content-Length", str(LIMITE_CORPO + 1))
            conexao.endheaders()
            resposta = conexao.getresponse()
            self.assertEqual(resposta.status, 413)
            resposta.read()
        finally:
            conexao.close()

    def test_content_length_ausente(self):
        conexao = http.client.HTTPConnection(self.host, self.porta, timeout=5)
        try:
            conexao.putrequest("POST", "/api/analisar")
            conexao.putheader("Content-Type", "application/json")
            conexao.endheaders()
            resposta = conexao.getresponse()
            self.assertEqual(resposta.status, 411)
            resposta.read()
        finally:
            conexao.close()

    def test_content_type_com_charset(self):
        status, _, _ = self.requisitar(
            "/api/analisar", metodo="POST",
            corpo=b'{"fonte": "emitir \\"A\\";"}',
            cabecalhos={"Content-Type": "application/json; charset=utf-8"})
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
