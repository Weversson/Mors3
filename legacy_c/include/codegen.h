#ifndef MORSE_CODEGEN_H
#define MORSE_CODEGEN_H

#include "ast.h"

typedef struct {
    int freq;
    int wpm;
    const char *base;
} CodegenOptions;

int codegen_emit(const Document *doc, const CodegenOptions *opt);

#endif