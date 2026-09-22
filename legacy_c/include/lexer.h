#ifndef MORSE_LEXER_H
#define MORSE_LEXER_H

#include <stddef.h>

typedef enum {
    TOK_SYMBOL,
    TOK_SPACE,
    TOK_EOF
} TokenKind;

typedef struct {
    TokenKind kind;
    int value;
} Token;

typedef struct {
    const char *src;
    size_t len;
    size_t pos;
} Lexer;

void lexer_init(Lexer *lx, const char *src, size_t len);
Token lexer_next(Lexer *lx);

#endif