"""Diagnósticos da análise semântica de MorseLang."""


class ErroSemantico(Exception):
    """Falha semântica, com posição na fonte contada a partir de 1."""

    def __init__(self, linha: int, coluna: int, detalhe: str) -> None:
        self.linha = linha
        self.coluna = coluna
        self.detalhe = detalhe
        super().__init__(f"linha {linha}, coluna {coluna}: {detalhe}")
