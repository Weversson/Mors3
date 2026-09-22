#ifndef MORSE_WAV_H
#define MORSE_WAV_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    int16_t *data;
    size_t len;
    size_t cap;
    uint32_t sample_rate;
} WavBuffer;

void wav_init(WavBuffer *w, uint32_t sample_rate);
void wav_free(WavBuffer *w);
void wav_tone(WavBuffer *w, double freq, double seconds);
void wav_silence(WavBuffer *w, double seconds);
int wav_write(WavBuffer *w, const char *path);

#endif