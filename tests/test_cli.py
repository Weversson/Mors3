import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(ROOT / "mfcc.py"), *args],
        capture_output=True, text=True, cwd=cwd,
    )


class CliHelpTest(unittest.TestCase):
    def test_help_exits_zero(self):
        r = _run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Compila um arquivo de texto", r.stdout)

    def test_help_short_flag(self):
        r = _run("-h")
        self.assertEqual(r.returncode, 0)

    def test_unknown_option_fails(self):
        r = _run("--bogus")
        self.assertNotEqual(r.returncode, 0)

    def test_missing_input_fails(self):
        r = _run()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("usage", r.stderr.lower())


class CliCompileTest(unittest.TestCase):
    def test_no_input_file(self):
        r = _run("nao_existe.mf")
        self.assertEqual(r.returncode, 1)
        self.assertIn("não foi possível ler", r.stderr)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "vazio.mf")
            Path(src).write_text("", encoding="utf-8")
            r = _run(src)
            self.assertEqual(r.returncode, 1)
            self.assertIn("nenhum texto", r.stderr)

    def test_only_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "com.mf")
            Path(src).write_text("// so comentario\n", encoding="utf-8")
            r = _run(src)
            self.assertEqual(r.returncode, 1)

    def test_sos_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "sos.mf"
            src.write_text("SOS\n", encoding="utf-8")
            base = str(src.with_suffix(""))
            r = _run(str(src))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((src.with_suffix(".morse")).read_text(encoding="utf-8"),
                             "... --- ...\n")
            with wave.open(base + ".wav", "rb") as w:
                self.assertEqual(w.getframerate(), 44100)

    def test_custom_output_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "x.mf"
            src.write_text("AB", encoding="utf-8")
            out = Path(tmp) / "custom"
            r = _run(str(src), "-o", str(out))
            self.assertEqual(r.returncode, 0)
            self.assertTrue(Path(str(out) + ".morse").exists())
            self.assertTrue(Path(str(out) + ".wav").exists())
            self.assertIn("custom.morse", r.stdout)

    def test_example_compiles(self):
        r = _run(str(ROOT / "examples" / "olamundo.mf"), "-o", "/tmp/mfcc_example_t")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_freq_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "f.mf"
            src.write_text("E", encoding="utf-8")
            r = _run(str(src), "--freq", "50")
            self.assertNotEqual(r.returncode, 0)
            r2 = _run(str(src), "--freq", "700", "--wpm", "30")
            self.assertEqual(r2.returncode, 0, r2.stderr)

    def test_unsupported_character_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "w.mf"
            src.write_text("Oi 😀\n", encoding="utf-8")
            r = _run(str(src))
            self.assertEqual(r.returncode, 0)
            self.assertIn("1 caractere(s)", r.stderr)


class CliCustomDirTest(unittest.TestCase):
    def test_runs_from_other_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "y.mf"
            src.write_text("SOS", encoding="utf-8")
            r = _run(str(src), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(tmp) / "y.morse").exists())


if __name__ == "__main__":
    unittest.main()