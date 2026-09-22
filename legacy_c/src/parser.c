#include "parser.h"

#include "lexer.h"
#include "morse.h"

#include <stdlib.h>

Document *parse_source(const char *src, size_t len, size_t *warnings) {
    if (!src) return NULL;
    if (warnings) *warnings = 0;

    Document *doc = calloc(1, sizeof *doc);
    if (!doc) return NULL;

    Lexer lx;
    lexer_init(&lx, src, len);

    int pending = 1;

    for (;;) {
        Token tok = lexer_next(&lx);
        if (tok.kind == TOK_EOF) break;

        if (tok.kind == TOK_SPACE) {
            pending = 1;
            continue;
        }

        const char *code = morse_for(tok.value);
        if (!code) {
            if (warnings) (*warnings)++;
            continue;
        }

        if (pending) {
            if (doc_push_word(doc) != 0) {
                doc_free(doc);
                return NULL;
            }
        }
        Word *w = &doc->words[doc->len - 1];
        word_push_sym(w, tok.value, code);
        pending = 0;
    }

    return doc;
}