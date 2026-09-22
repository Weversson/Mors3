#include "codegen.h"

#include "morse.h"
#include "wav.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} Str;

static int str_append(Str *s, const char *p, size_t n) {
    if (s->len + n + 1 > s->cap) {
        size_t nc = s->cap ? s->cap : 64;
        while (nc < s->len + n + 1) nc *= 2;
        char *nd = realloc(s->data, nc);
        if (!nd) return -1;
        s->data = nd;
        s->cap = nc;
    }
    memcpy(s->data + s->len, p, n);
    s->len += n;
    s->data[s->len] = '\0';
    return 0;
}

static char *morse_to_text(const Document *doc) {
    Str out = {0};

    for (size_t w = 0; w < doc->len; w++) {
        const Word *word = &doc->words[w];
        if (w > 0 && str_append(&out, "   ", 3) != 0) goto fail;
        for (size_t s = 0; s < word->len; s++) {
            if (s > 0 && str_append(&out, " ", 1) != 0) goto fail;
            if (str_append(&out, word->syms[s].morse,
                           strlen(word->syms[s].morse)) != 0) goto fail;
        }
    }

    if (!out.data) {
        out.data = malloc(1);
        if (out.data) out.data[0] = '\0';
    }
    return out.data;

fail:
    free(out.data);
    return NULL;
}

static void build_audio(const Document *doc, WavBuffer *wav,
                        const CodegenOptions *opt) {
    double unit = 1.2 / (double)opt->wpm;
    int start = 1;

    for (size_t w = 0; w < doc->len; w++) {
        const Word *word = &doc->words[w];
        for (size_t s = 0; s < word->len; s++) {
            if (!start) wav_silence(wav, 3.0 * unit);
            const char *m = word->syms[s].morse;
            for (size_t i = 0; m[i]; i++) {
                if (i > 0) wav_silence(wav, unit);
                wav_tone(wav, (double)opt->freq,
                         m[i] == '.' ? unit : 3.0 * unit);
            }
            start = 0;
        }
        if (w + 1 < doc->len) wav_silence(wav, 4.0 * unit);
    }
}

int codegen_emit(const Document *doc, const CodegenOptions *opt) {
    if (!doc || !opt) return -1;

    char morse_path[2048];
    char wav_path[2048];
    if (snprintf(morse_path, sizeof morse_path, "%s.morse", opt->base) >=
        (int)sizeof morse_path)
        return -1;
    if (snprintf(wav_path, sizeof wav_path, "%s.wav", opt->base) >=
        (int)sizeof wav_path)
        return -1;

    char *text = morse_to_text(doc);
    if (!text) return -1;

    FILE *f = fopen(morse_path, "w");
    if (!f) {
        free(text);
        return -1;
    }
    fputs(text, f);
    fputc('\n', f);
    fclose(f);
    free(text);

    WavBuffer wav;
    wav_init(&wav, 44100);
    build_audio(doc, &wav, opt);
    int rc = wav_write(&wav, wav_path);
    wav_free(&wav);
    return rc;
}