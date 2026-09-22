import tempfile
import unittest
import wave
from pathlib import Path

from src.build_ast import parse_source
from src.codegen import emit, morse_to_text


class MorseTextTest(unittest.TestCase):
    def test_word_and_letter_separators(self):
        doc, _ = parse_source("HELLO WORLD")
        self.assertEqual(morse_to_text(doc),
                         ".... . .-.. .-.. ---   .-- --- .-. .-.. -..\n")

    def test_sos(self):
        doc, _ = parse_source("SOS")
        self.assertEqual(morse_to_text(doc), "... --- ...\n")

    def test_single_letter(self):
        doc, _ = parse_source("A")
        self.assertEqual(morse_to_text(doc), ".-\n")

    def test_empty_document_returns_only_newline(self):
        from src.ast import Document

        self.assertEqual(morse_to_text(Document()), "\n")


class EmitTest(unittest.TestCase):
    def test_emit_writes_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp) / "out")
            doc, _ = parse_source("SOS")
            morse_path, wav_path = emit(doc, base, freq=600, wpm=20)

            self.assertEqual(morse_path, base + ".morse")
            self.assertEqual(wav_path, base + ".wav")
            self.assertTrue(Path(morse_path).exists())
            self.assertTrue(Path(wav_path).exists())

            with open(morse_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "... --- ...\n")

            with wave.open(wav_path, "rb") as w:
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getframerate(), 44100)

    def test_emit_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp) / "m")
            doc, _ = parse_source("hello 1 2")
            morse_path, _ = emit(doc, base, 600, 20)
            with open(morse_path, encoding="utf-8") as f:
                self.assertEqual(
                    f.read(),
                    ".... . .-.. .-.. ---   .----   ..---\n")

    def test_emit_respects_wpm_and_freq_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp) / "m")
            doc, _ = parse_source("E")
            emit(doc, base, freq=800, wpm=10)
            with wave.open(base + ".wav", "rb") as w:
                frames = w.readframes(w.getnframes())
            unit = 1.2 / 10
            self.assertEqual(len(frames), 2 * int(unit * 44100))


if __name__ == "__main__":
    unittest.main()