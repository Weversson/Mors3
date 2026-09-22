from dataclasses import dataclass, field


@dataclass
class Sym:
    given: str
    morse: str


@dataclass
class Word:
    syms: list[Sym] = field(default_factory=list)


@dataclass
class Document:
    words: list[Word] = field(default_factory=list)