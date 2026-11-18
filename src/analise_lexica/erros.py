"""Diagnósticos da análise léxica de MorseLang."""


class ErroLexico(Exception):
    """Falha de reconhecimento de tokens, com posição na fonte.

    Linhas e colunas são contadas a partir de 1, como na CLI e na especificação.
    """

    def __init__(self, linha: int, coluna: int, detalhe: str) -> None:
        self.linha = linha
        self.coluna = coluna
        self.detalhe = detalhe
        super().__init__(f"linha {linha}, coluna {coluna}: {detalhe}")
