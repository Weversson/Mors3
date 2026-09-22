#ifndef MORSE_AST_H
#define MORSE_AST_H

#include <stddef.h>

typedef struct Sym {
    int given;
    char morse[8];
} Sym;

typedef struct Word {
    Sym *syms;
    size_t len;
    size_t cap;
} Word;

typedef struct Document {
    Word *words;
    size_t len;
    size_t cap;
} Document;

int word_push_sym(Word *w, int given, const char *code);
int doc_push_word(Document *d);
void doc_free(Document *d);

#endif