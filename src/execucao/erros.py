"""Diagnósticos da etapa de execução de MorseLang."""


class ErroExecucao(Exception):
    """Falha ao expandir ou transformar um programa em timeline.

    A análise semântica já garante as regras da linguagem. Este erro cobre usos
    diretos da API com uma AST não validada e limites de segurança opcionais da
    expansão.
    """
