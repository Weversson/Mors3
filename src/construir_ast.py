"""Converte a árvore concreta do ANTLR na AST da linguagem MorseLang."""

from gerado.MorseLangParserVisitor import MorseLangParserVisitor

from .ast_morselang import (
    Concatenacao, Emissao, Mensagem, Numero, Programa, Referencia,
    Repeticao, Texto, Tom, Velocidade,
)


def _posicao(token):
    return {"linha": token.line, "coluna": token.column + 1}


class ConstruirAST(MorseLangParserVisitor):
    def visitPrograma(self, ctx):
        comandos = [self.visit(filho) for filho in ctx.preambulo().getChildren()]
        comandos.extend(self.visit(emissao) for emissao in ctx.emissao())
        return Programa(**_posicao(ctx.start), comandos=tuple(comandos))

    def visitDeclaracao(self, ctx):
        return Mensagem(**_posicao(ctx.start), nome=ctx.IDENT().getText(),
                        expressao=self.visit(ctx.expressao()))

    def visitConfiguracaoTom(self, ctx):
        token = (ctx.REAL() or ctx.INTEIRO()).symbol
        return Tom(**_posicao(ctx.start),
                   valor=Numero(**_posicao(token), lexema=token.text))

    def visitConfiguracaoVelocidade(self, ctx):
        token = ctx.INTEIRO().symbol
        return Velocidade(**_posicao(ctx.start),
                          valor=Numero(**_posicao(token), lexema=token.text))

    def visitEmissao(self, ctx):
        return Emissao(**_posicao(ctx.start), expressao=self.visit(ctx.expressao()))

    def visitExpressao(self, ctx):
        termos = ctx.termo()
        resultado = self.visit(termos[0])
        for termo in termos[1:]:
            resultado = Concatenacao(**_posicao(ctx.start), esquerda=resultado,
                                     direita=self.visit(termo))
        return resultado

    def visitTermo(self, ctx):
        resultado = self.visit(ctx.atomo())
        for inteiro in ctx.INTEIRO():
            token = inteiro.symbol
            resultado = Repeticao(
                **_posicao(ctx.start), texto=resultado,
                quantidade=Numero(**_posicao(token), lexema=token.text),
            )
        return resultado

    def visitAtomo(self, ctx):
        if ctx.TEXTO() is not None:
            return Texto(**_posicao(ctx.start), valor=ctx.TEXTO().getText()[1:-1])
        if ctx.IDENT() is not None:
            return Referencia(**_posicao(ctx.start), nome=ctx.IDENT().getText())
        return self.visit(ctx.expressao())
