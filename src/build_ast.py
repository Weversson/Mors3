from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from generated.MorseLexer import MorseLexer
from generated.MorseListener import MorseListener
from generated.MorseParser import MorseParser

from . import morse_tables
from .ast import Document, Sym, Word


class BuildAstListener(MorseListener):
    def __init__(self) -> None:
        self.doc = Document()
        self.warnings = 0

    def enterWord(self, ctx: MorseParser.WordContext) -> None:
        word = Word()
        for tok in ctx.SYMBOL():
            ch = tok.getText()
            code = morse_tables.morse_for(ch)
            if code is None:
                self.warnings += 1
                continue
            word.syms.append(Sym(given=ch, morse=code))
        if word.syms:
            self.doc.words.append(word)


def parse_source(source: str) -> tuple[Document, int]:
    lexer = MorseLexer(InputStream(source))
    tokens = CommonTokenStream(lexer)
    parser = MorseParser(tokens)
    tree = parser.doc()
    listener = BuildAstListener()
    ParseTreeWalker().walk(listener, tree)
    return listener.doc, listener.warnings