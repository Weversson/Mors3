import unittest

from src.build_ast import parse_source


class DocStructureTest(unittest.TestCase):
    def test_simple_sentence(self):
        doc, warnings = parse_source("HELLO WORLD")
        self.assertEqual(warnings, 0)
        self.assertEqual(len(doc.words), 2)
        self.assertEqual("".join(s.given for s in doc.words[0].syms), "HELLO")
        self.assertEqual("".join(s.given for s in doc.words[1].syms), "WORLD")
        self.assertEqual([s.morse for s in doc.words[0].syms],
                         ["....", ".", ".-..", ".-..", "---"])
        self.assertEqual([s.morse for s in doc.words[1].syms],
                         [".--", "---", ".-.", ".-..", "-.."])

    def test_sos_decode(self):
        doc, _ = parse_source("SOS")
        self.assertEqual([s.morse for s in doc.words[0].syms],
                         ["...", "---", "..."])

    def test_whitespace_variants(self):
        doc, _ = parse_source("a\tb\nc")
        self.assertEqual(["a", "b", "c"], [w.syms[0].given for w in doc.words])

    def test_multiple_spaces_collapse(self):
        doc, _ = parse_source("a   b")
        self.assertEqual(len(doc.words), 2)

    def test_trailing_leading_whitespace(self):
        doc, _ = parse_source("  abc  ")
        self.assertEqual(len(doc.words), 1)
        self.assertEqual(doc.words[0].syms[0].given, "a")

    def test_empty_source(self):
        doc, _ = parse_source("")
        self.assertEqual(len(doc.words), 0)

    def test_only_whitespace(self):
        doc, _ = parse_source(" \t\n  \n")
        self.assertEqual(len(doc.words), 0)

    def test_only_comments(self):
        doc, _ = parse_source("// nada aqui\n// nem aqui")
        self.assertEqual(len(doc.words), 0)

    def test_comment_inside_word(self):
        doc, warnings = parse_source("ab//cd")
        self.assertEqual(warnings, 0)
        self.assertEqual(len(doc.words), 1)
        self.assertEqual("".join(s.given for s in doc.words[0].syms), "ab")

    def test_comment_until_end_of_line(self):
        doc, _ = parse_source("ab//cd\nef")
        self.assertEqual(len(doc.words), 2)
        self.assertEqual("".join(s.given for s in doc.words[0].syms), "ab")
        self.assertEqual("".join(s.given for s in doc.words[1].syms), "ef")

    def test_comment_without_newline_at_eof(self):
        doc, _ = parse_source("abc// fim sem quebra de linha")
        self.assertEqual(len(doc.words), 1)
        self.assertEqual("".join(s.given for s in doc.words[0].syms), "abc")

    def test_single_slash_is_symbol(self):
        doc, _ = parse_source("/ abc")
        self.assertEqual(len(doc.words), 2)
        self.assertEqual(doc.words[0].syms[0].given, "/")
        self.assertEqual(doc.words[0].syms[0].morse, "-..-.")
        self.assertEqual(doc.words[1].syms[0].given, "a")

    def test_punctuation_mixed_in_word(self):
        doc, _ = parse_source("Ola, mundo!")
        self.assertEqual(len(doc.words), 2)
        self.assertEqual("".join(s.given for s in doc.words[0].syms), "Ola,")
        self.assertEqual("".join(s.given for s in doc.words[1].syms), "mundo!")

    def test_accents_in_word(self):
        doc, warnings = parse_source("ção")
        self.assertEqual(warnings, 0)
        self.assertEqual([s.given for s in doc.words[0].syms], ["ç", "ã", "o"])
        self.assertEqual([s.morse for s in doc.words[0].syms], ["-.-.", ".-", "---"])

    def test_unsupported_chars_warn_and_skip(self):
        doc, warnings = parse_source("Oi € 👍tudo")
        self.assertEqual(warnings, 2)
        words = ["".join(s.given for s in w.syms) for w in doc.words]
        self.assertEqual(len(doc.words), 2)
        self.assertEqual(words[0], "Oi")
        self.assertEqual(words[1], "tudo")

    def test_ast_types(self):
        from src.ast import Document, Sym, Word

        doc, _ = parse_source("OK")
        self.assertIsInstance(doc, Document)
        self.assertIsInstance(doc.words[0], Word)
        self.assertIsInstance(doc.words[0].syms[0], Sym)

    def test_parse_is_reusable(self):
        doc1, _ = parse_source("UM")
        doc2, _ = parse_source("DOIS")
        self.assertEqual(len(doc1.words), 1)
        self.assertEqual(len(doc2.words), 1)
        self.assertIsNot(doc1, doc2)


if __name__ == "__main__":
    unittest.main()