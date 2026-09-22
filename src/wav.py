import array
import math
import wave

_DOT_UNITS = 1.0
_DASH_UNITS = 3.0
_ELEM_GAP_UNITS = 1.0
_CHAR_GAP_UNITS = 3.0
_WORD_GAP_UNITS = 7.0


def _tone(freq: float, seconds: float, sample_rate: int, frames: array.array) -> None:
    n = int(seconds * sample_rate)
    step = 2.0 * math.pi * freq / sample_rate
    for i in range(n):
        frames.append(int(0.5 * 32767.0 * math.sin(step * i)))


def _silence(seconds: float, sample_rate: int, frames: array.array) -> None:
    n = int(seconds * sample_rate)
    frames.extend([0] * n)


def write_audio(doc, path: str, freq: int = 600, wpm: int = 20,
                sample_rate: int = 44100) -> None:
    unit = 1.2 / wpm
    frames = array.array("h")
    start = False
    words = doc.words

    for wi, word in enumerate(words):
        for sym in word.syms:
            if start:
                _silence(_CHAR_GAP_UNITS * unit, sample_rate, frames)
            for i, ch in enumerate(sym.morse):
                if i > 0:
                    _silence(_ELEM_GAP_UNITS * unit, sample_rate, frames)
                dur = (_DASH_UNITS if ch == "-" else _DOT_UNITS) * unit
                _tone(freq, dur, sample_rate, frames)
            start = True
        if wi + 1 < len(words):
            _silence((_WORD_GAP_UNITS - _CHAR_GAP_UNITS) * unit,
                     sample_rate, frames)

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(frames.tobytes())