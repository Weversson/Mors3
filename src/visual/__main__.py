"""CLI do servidor local de visualização de MorseLang."""

import argparse
import sys
import threading
import webbrowser

from .api import LIMITE_PADRAO
from .servidor import criar_servidor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visual",
        description=(
            "Sobe a visualização web local de MorseLang em tempo real."
        ),
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="endereço de escuta (padrão: 127.0.0.1)",
    )
    parser.add_argument(
        "--porta", type=int, default=8000,
        help="porta HTTP (padrão: 8000; 0 escolhe uma porta livre)",
    )
    parser.add_argument(
        "--limite", type=int, default=LIMITE_PADRAO,
        help=f"limite de caracteres expandidos (padrão: {LIMITE_PADRAO})",
    )
    parser.add_argument(
        "--abrir", action="store_true",
        help="abre a página no navegador padrão",
    )
    parser.add_argument(
        "--verboso", action="store_true",
        help="registra cada requisição no terminal",
    )
    args = parser.parse_args(argv)

    if not 0 <= args.porta <= 65535:
        parser.error("--porta deve estar entre 0 e 65535")
    if args.limite < 0:
        parser.error("--limite deve ser não negativo")

    try:
        servidor = criar_servidor(
            args.host,
            args.porta,
            limite_caracteres=args.limite,
            verboso=args.verboso,
        )
    except OSError as erro:
        print(f"erro: não foi possível iniciar o servidor: {erro}",
              file=sys.stderr)
        return 1

    host, porta = servidor.server_address[:2]
    if host in ("0.0.0.0", "127.0.0.1", "::1"):
        host = "localhost"
    url = f"http://{host}:{porta}/"
    print(f"MorseLang visual em {url}")
    print("Pressione Ctrl+C para encerrar.")

    if args.abrir:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
