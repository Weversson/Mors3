import array
import tempfile
import unittest
import wave
from pathlib import Path

from src.build_ast import parse_source
from src.wav import write_audio

SR = 44100
WPM = 20
UNIT_SAMPLES = 2646          # 1.2/20 s * 44100 Hz


def _read_frames(path):
    with wave.open(path, "rb") as w:
        return w, array.array("h", w.readframes(w.getnframes()))


def _count_tone_samples(frames):
    return sum(1 for s in frames if s != 0)


class WavStructureTest(unittest.TestCase):
    def test_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sos.wav")
            doc, _ = parse_source("SOS")
            write_audio(doc, path, freq=600, wpm=WPM)

            with wave.open(path, "rb") as w:
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getframerate(), SR)

    def test_amplitude_not_full_scale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sos.wav")
            write_audio(parse_source("E")[0], path, freq=600, wpm=WPM)
            _, frames = _read_frames(path)
            self.assertLessEqual(max(frames), int(0.5 * 32767) + 1)
            self.assertGreater(len(frames), 0)

    def test_contains_silence_and_tone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sos.wav")
            write_audio(parse_source("SOS")[0], path, freq=600, wpm=WPM)
            _, frames = _read_frames(path)
            self.assertTrue(any(s == 0 for s in frames))
            self.assertTrue(any(s != 0 for s in frames))


class WavTimingTest(unittest.TestCase):
    def test_sos_duration(self):
        # SOS = S(5u) + 3u + O(11u) + 3u + S(5u) = 27 unidades = 1.62 s
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sos.wav")
            write_audio(parse_source("SOS")[0], path, freq=600, wpm=WPM)
            w, frames = _read_frames(path)
            self.assertAlmostEqual(w.getnframes() / SR, 27 * 1.2 / WPM, delta=0.01)

    def test_tone_samples_for_sos(self):
        # S: 3 pontos = 3u ; O: 3 traços = 9u ; S: 3u  => 15u de tom
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sos.wav")
            write_audio(parse_source("SOS")[0], path, freq=600, wpm=WPM)
            _, frames = _read_frames(path)
            expected_tone = (3 + 9 + 3) * UNIT_SAMPLES
            self.assertAlmostEqual(_count_tone_samples(frames), expected_tone,
                                   delta=UNIT_SAMPLES // 2)

    def test_hello_world_sos_duration(self):
        # 145 unidades de 0.06 s = 8.7 s (conferido com a versão C)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "hw.wav")
            write_audio(parse_source("HELLO WORLD SOS")[0], path, freq=600, wpm=WPM)
            w, _ = _read_frames(path)
            self.assertAlmostEqual(w.getnframes() / SR, 8.7, delta=0.01)

    def test_word_gap_exists(self):
        # "A B" tem gap de palavra de 7 unidades entre as duas letras;
        # a duração total deve ser maior que "AB" (com gap de char de 3u).
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp) / "g")
            write_audio(parse_source("A B")[0], base + ".wav", freq=600, wpm=WPM)
            write_audio(parse_source("AB")[0], base + "2.wav", freq=600, wpm=WPM)
            t1 = wave.open(base + ".wav", "rb").getnframes()
            t2 = wave.open(base + "2.wav", "rb").getnframes()
            self.assertGreater(t1, t2)
            self.assertEqual(t1 - t2, 4 * UNIT_SAMPLES)  # 7u - 3u


class WavToneTest(unittest.TestCase):
    def test_dot_frequency_around_600hz(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "e.wav")
            write_audio(parse_source("E")[0], path, freq=600, wpm=WPM)
            _, frames = _read_frames(path)

            # cruza por zero da primeira metade (o ponto E = 1 unidade)
            dot_end = UNIT_SAMPLES
            crossings = sum(
                1 for i in range(1, dot_end)
                if (frames[i - 1] < 0) != (frames[i] < 0)
            )
            # 600 Hz por 0.06 s => ~36 ciclos => ~72 cruzamentos
            self.assertGreater(crossings, 66)
            self.assertLess(crossings, 78)

    def test_dash_is_three_times_dot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp) / "dash")
            write_audio(parse_source("T")[0], base + ".wav", freq=600, wpm=WPM)  # T = -
            w, _ = _read_frames(base + ".wav")
            self.assertEqual(w.getnframes(), 3 * UNIT_SAMPLES)


if __name__ == "__main__":
    unittest.main()