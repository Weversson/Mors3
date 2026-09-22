import unittest

from src import morse_tables as mt


class MorseTablesTest(unittest.TestCase):
    def test_letters(self):
        for ch, expected in {
            "A": ".-",
            "B": "-...",
            "C": "-.-.",
            "E": ".",
            "H": "....",
            "M": "--",
            "O": "---",
            "S": "...",
            "X": "-..-",
        }.items():
            self.assertEqual(mt.morse_for(ch), expected, f"letra {ch}")

    def test_all_letters_supported(self):
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            self.assertIsNotNone(mt.morse_for(ch), f"faltou {ch}")

    def test_digits(self):
        self.assertEqual(mt.morse_for("0"), "-----")
        self.assertEqual(mt.morse_for("5"), ".....")
        self.assertEqual(mt.morse_for("9"), "----.")
        for d in "0123456789":
            self.assertIsNotNone(mt.morse_for(d))

    def test_case_insensitive(self):
        self.assertEqual(mt.morse_for("a"), mt.morse_for("A"))
        self.assertEqual(mt.morse_for("z"), "--..")

    def test_punctuation(self):
        for ch, expected in {
            ".": ".-.-.-",
            ",": "--..--",
            "?": "..--..",
            "!": "-.-.--",
            "/": "-..-.",
            "(": "-.--.",
            ")": "-.--.-",
            ":": "---...",
            ";": "-.-.-.",
            "=": "-...-",
            "+": ".-.-.",
            "-": "-....-",
            "_": "..--.-",
            '"': ".-..-.",
            "$": "...-..-",
            "@": ".--.-.",
            "&": ".-...",
            "'": ".----.",
        }.items():
            self.assertEqual(mt.morse_for(ch), expected, f"símbolo {ch}")

    def test_accents_normalized(self):
        self.assertEqual(mt.morse_for("Á"), ".-")   # Á -> A
        self.assertEqual(mt.morse_for("ã"), ".-")   # ã -> A
        self.assertEqual(mt.morse_for("É"), ".")    # É -> E
        self.assertEqual(mt.morse_for("ç"), "-.-.") # ç -> C
        self.assertEqual(mt.morse_for("ñ"), "-.")   # ñ -> N
        self.assertEqual(mt.morse_for("Ü"), "..-")  # Ü -> U
        self.assertEqual(mt.morse_for("ó"), "---")  # ó -> O

    def test_unsupported(self):
        self.assertIsNone(mt.morse_for("€"))
        self.assertIsNone(mt.morse_for("😀"))
        self.assertIsNone(mt.morse_for("§"))
        self.assertIsNone(mt.morse_for(" "))

    def test_normalize_identity_for_plain(self):
        self.assertEqual(mt.normalize("c"), "C")
        self.assertEqual(mt.normalize("5"), "5")


if __name__ == "__main__":
    unittest.main()