"""Servidor HTTP local da visualização de MorseLang.

Usa apenas a biblioteca padrão. A página estática fica em ``web/`` e consome a
API por ``POST /api/analisar``. O servidor é destinado a uso local, não exposto
à rede por padrão.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from src.geracao import gerar_morse, gerar_wav

from .api import LIMITE_PADRAO, analisar, analisar_timeline

DIRETORIO_WEB = Path(__file__).resolve().parent / "web"
LIMITE_CORPO = 1_000_000

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class ServidorVisual(ThreadingHTTPServer):
    """Servidor concorrente com a configuração usada pelos manipuladores."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        endereco,
        manipulador,
        *,
        diretorio_web: Path = DIRETORIO_WEB,
        limite_caracteres: int | None = LIMITE_PADRAO,
        verboso: bool = False,
    ) -> None:
        super().__init__(endereco, manipulador)
        self.diretorio_web = Path(diretorio_web).resolve()
        self.limite_caracteres = limite_caracteres
        self.verboso = verboso


class _Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MorseLangVisual/1.0"

    # Silencia o log padrão, que escreve uma linha por requisição.
    def log_message(self, formato, *argumentos) -> None:
        if getattr(self.server, "verboso", False):
            super().log_message(formato, *argumentos)

    def _responder(
        self,
        status: int,
        corpo: bytes,
        tipo: str,
        *,
        cabecalhos: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        for nome, valor in (cabecalhos or {}).items():
            self.send_header(nome, valor)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(corpo)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _responder_json(
        self,
        status: int,
        dados: dict,
        *,
        cabecalhos: dict[str, str] | None = None,
    ) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self._responder(
            status, corpo, "application/json; charset=utf-8",
            cabecalhos=cabecalhos)

    def _erro_requisicao(self, status: int, detalhe: str) -> None:
        self._responder_json(
            status, {"ok": False, "etapa": "requisicao", "detalhe": detalhe})

    def _receber_json(self) -> dict | None:
        """Lê e valida o corpo JSON; responde ao cliente em caso de falha."""
        tipo = self.headers.get("Content-Type", "")
        if not tipo.lower().startswith("application/json"):
            self._erro_requisicao(
                415, "Content-Type deve ser application/json")
            return None

        tamanho_texto = self.headers.get("Content-Length")
        if tamanho_texto is None:
            self._erro_requisicao(411, "Content-Length é obrigatório")
            return None
        try:
            tamanho = int(tamanho_texto)
        except ValueError:
            self._erro_requisicao(400, "Content-Length inválido")
            return None
        if tamanho < 0:
            self._erro_requisicao(400, "Content-Length inválido")
            return None
        if tamanho > LIMITE_CORPO:
            self._erro_requisicao(
                413, f"corpo maior que {LIMITE_CORPO} bytes")
            return None

        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._erro_requisicao(400, "JSON inválido")
            return None
        if not isinstance(dados, dict):
            self._erro_requisicao(400, "o corpo deve ser um objeto JSON")
            return None
        return dados

    def _exportar(self, fonte: str, limite: int | None, dados: dict) -> None:
        formato = dados.get("formato")
        if formato not in ("morse", "wav"):
            self._erro_requisicao(
                400, "o campo 'formato' deve ser 'morse' ou 'wav'")
            return

        timeline, erro = analisar_timeline(fonte, limite_caracteres=limite)
        if erro is not None:
            self._responder_json(200, erro)
            return
        assert timeline is not None

        if formato == "morse":
            corpo = gerar_morse(timeline).encode("utf-8")
            tipo = "text/plain; charset=utf-8"
        else:
            corpo = gerar_wav(timeline)
            tipo = "audio/wav"
        self._responder(200, corpo, tipo, cabecalhos={
            "Content-Disposition": f'attachment; filename="morselang.{formato}"',
        })

    def _servir_estatico(self, caminho: str) -> None:
        if caminho in ("", "/"):
            caminho = "/index.html"
        relativo = caminho.lstrip("/")
        base = self.server.diretorio_web
        destino = (base / relativo).resolve()
        if not destino.is_relative_to(base) or not destino.is_file():
            self._erro_requisicao(404, "arquivo não encontrado")
            return

        tipo = TIPOS.get(destino.suffix.lower())
        if tipo is None:
            tipo = mimetypes.guess_type(destino.name)[0] or (
                "application/octet-stream")
        try:
            corpo = destino.read_bytes()
        except OSError:
            self._erro_requisicao(404, "arquivo não encontrado")
            return
        self._responder(200, corpo, tipo)

    def do_GET(self) -> None:
        caminho = unquote(urlparse(self.path).path)
        if caminho in ("/api/saude", "/health"):
            self._responder_json(200, {
                "ok": True,
                "servico": "morselang-visual",
                "api": "/api/analisar",
                "limite_caracteres": self.server.limite_caracteres,
            })
            return
        if caminho in ("/api/analisar", "/api/exportar"):
            self._responder_json(
                405,
                {"ok": False, "etapa": "requisicao",
                 "detalhe": "use POST nesta rota"},
                cabecalhos={"Allow": "POST"},
            )
            return
        if caminho.startswith("/api/"):
            self._erro_requisicao(404, "rota não encontrada")
            return
        self._servir_estatico(caminho)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        caminho = unquote(urlparse(self.path).path)
        if caminho not in ("/api/analisar", "/api/exportar"):
            if caminho in ("/api/saude", "/health"):
                self._responder_json(
                    405,
                    {"ok": False, "etapa": "requisicao",
                     "detalhe": "use GET"},
                    cabecalhos={"Allow": "GET"},
                )
            else:
                self._erro_requisicao(404, "rota não encontrada")
            return

        dados = self._receber_json()
        if dados is None:
            return

        fonte = dados.get("fonte")
        if not isinstance(fonte, str):
            self._erro_requisicao(
                400, "o campo 'fonte' deve ser uma string")
            return

        limite = self.server.limite_caracteres
        if "limite" in dados:
            valor = dados["limite"]
            if (isinstance(valor, bool) or not isinstance(valor, int)
                    or valor < 0):
                self._erro_requisicao(
                    400, "o campo 'limite' deve ser um inteiro não negativo")
                return
            if limite is None or valor < limite:
                limite = valor

        try:
            if caminho == "/api/exportar":
                self._exportar(fonte, limite, dados)
            else:
                self._responder_json(
                    200, analisar(fonte, limite_caracteres=limite))
        except Exception as erro:  # proteção para não derrubar o servidor
            if getattr(self.server, "verboso", False):
                import traceback
                traceback.print_exc()
            self._responder_json(500, {
                "ok": False,
                "etapa": "interno",
                "detalhe": f"{type(erro).__name__}: {erro}",
            })


def criar_servidor(
    host: str = "127.0.0.1",
    porta: int = 8000,
    *,
    diretorio_web: Path = DIRETORIO_WEB,
    limite_caracteres: int | None = LIMITE_PADRAO,
    verboso: bool = False,
) -> ServidorVisual:
    """Cria o servidor, sem iniciar o laço de atendimento."""
    if limite_caracteres is not None and limite_caracteres < 0:
        raise ValueError("limite_caracteres deve ser não negativo")
    return ServidorVisual(
        (host, porta),
        _Manipulador,
        diretorio_web=diretorio_web,
        limite_caracteres=limite_caracteres,
        verboso=verboso,
    )
