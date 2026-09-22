#include "wav.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846264338327950288
#endif

void wav_init(WavBuffer *w, uint32_t sample_rate) {
    w->data = NULL;
    w->len = 0;
    w->cap = 0;
    w->sample_rate = sample_rate;
}

void wav_free(WavBuffer *w) {
    free(w->data);
    w->data = NULL;
    w->len = w->cap = 0;
}

static void reserve(WavBuffer *w, size_t n) {
    if (w->len + n > w->cap) {
        size_t nc = w->cap ? w->cap : 4096;
        while (nc < w->len + n) nc *= 2;
        int16_t *nd = realloc(w->data, nc * sizeof(int16_t));
        if (!nd) abort();
        w->data = nd;
        w->cap = nc;
    }
}

static void wav_push(WavBuffer *w, int16_t s) {
    reserve(w, 1);
    w->data[w->len++] = s;
}

void wav_tone(WavBuffer *w, double freq, double seconds) {
    size_t n = (size_t)(seconds * (double)w->sample_rate);
    double step = 2.0 * M_PI * freq / (double)w->sample_rate;
    for (size_t i = 0; i < n; i++) {
        int16_t s = (int16_t)(0.5 * 32767.0 * sin(step * (double)i));
        wav_push(w, s);
    }
}

void wav_silence(WavBuffer *w, double seconds) {
    size_t n = (size_t)(seconds * (double)w->sample_rate);
    for (size_t i = 0; i < n; i++) wav_push(w, 0);
}

int wav_write(WavBuffer *w, const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;

    uint32_t sr = w->sample_rate;
    uint32_t data_bytes = (uint32_t)(w->len * sizeof(int16_t));
    uint32_t bits = 16;

    struct {
        char riff[4];    uint32_t riff_sz;  char wave[4];
        char fmt[4];     uint32_t fmt_sz;   uint16_t fmt_tag;
        uint16_t channels; uint32_t sr;    uint32_t byte_rate;
        uint16_t block_align; uint16_t bits;
        char data[4];    uint32_t data_sz;
    } __attribute__((packed)) hdr;

    memcpy(hdr.riff, "RIFF", 4);
    hdr.riff_sz = 36 + data_bytes;
    memcpy(hdr.wave, "WAVE", 4);
    memcpy(hdr.fmt, "fmt ", 4);
    hdr.fmt_sz = 16;
    hdr.fmt_tag = 1;
    hdr.channels = 1;
    hdr.sr = sr;
    hdr.byte_rate = sr * 1 * (bits / 8);
    hdr.block_align = 1 * (bits / 8);
    hdr.bits = bits;
    memcpy(hdr.data, "data", 4);
    hdr.data_sz = data_bytes;

    fwrite(&hdr, sizeof hdr, 1, f);
    fwrite(w->data, sizeof(int16_t), w->len, f);
    fclose(f);
    return 0;
}