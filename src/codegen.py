from .wav import write_audio


def morse_to_text(doc) -> str:
    parts = []
    for i, word in enumerate(doc.words):
        if i:
            parts.append("   ")
        parts.append(" ".join(s.morse for s in word.syms))
    return "".join(parts) + "\n"


def emit(doc, base: str, freq: int, wpm: int) -> tuple[str, str]:
    base = str(base)
    morse_path = base + ".morse"
    wav_path = base + ".wav"

    with open(morse_path, "w", encoding="utf-8") as f:
        f.write(morse_to_text(doc))
    write_audio(doc, wav_path, freq=freq, wpm=wpm)

    return morse_path, wav_path