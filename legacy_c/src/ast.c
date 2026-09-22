#include "ast.h"

#include <stdlib.h>
#include <string.h>

int word_push_sym(Word *w, int given, const char *code) {
    if (w->len == w->cap) {
        size_t nc = w->cap ? w->cap * 2 : 8;
        Sym *ns = realloc(w->syms, nc * sizeof *ns);
        if (!ns) return -1;
        w->syms = ns;
        w->cap = nc;
    }
    size_t n = strlen(code);
    if (n >= sizeof w->syms[w->len].morse)
        n = sizeof w->syms[w->len].morse - 1;
    w->syms[w->len].given = given;
    memcpy(w->syms[w->len].morse, code, n);
    w->syms[w->len].morse[n] = '\0';
    w->len++;
    return 0;
}

int doc_push_word(Document *d) {
    if (d->len == d->cap) {
        size_t nc = d->cap ? d->cap * 2 : 16;
        Word *nw = realloc(d->words, nc * sizeof *nw);
        if (!nw) return -1;
        d->words = nw;
        d->cap = nc;
    }
    memset(&d->words[d->len], 0, sizeof d->words[d->len]);
    d->len++;
    return 0;
}

void doc_free(Document *d) {
    if (!d) return;
    for (size_t i = 0; i < d->len; i++) free(d->words[i].syms);
    free(d->words);
    free(d);
}