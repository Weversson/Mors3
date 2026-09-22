#include "lexer.h"

static int is_space(int c) {
    return c == ' ' || c == '\t' || c == '\n' ||
           c == '\r' || c == '\f' || c == '\v';
}

static int decode_utf8(const unsigned char *p, int avail) {
    if (p[0] < 0x80) return p[0];
    int cp, extra;
    if ((p[0] & 0xE0) == 0xC0) {
        extra = 1;
        cp = p[0] & 0x1F;
    } else if ((p[0] & 0xF0) == 0xE0) {
        extra = 2;
        cp = p[0] & 0x0F;
    } else if ((p[0] & 0xF8) == 0xF0) {
        extra = 3;
        cp = p[0] & 0x07;
    } else {
        return -1;
    }
    if (avail < extra + 1) return -1;
    for (int i = 1; i <= extra; i++) {
        if ((p[i] & 0xC0) != 0x80) return -1;
        cp = (cp << 6) | (p[i] & 0x3F);
    }
    return cp;
}

void lexer_init(Lexer *lx, const char *src, size_t len) {
    lx->src = src;
    lx->len = len;
    lx->pos = 0;
}

static void skip_comment(Lexer *lx) {
    while (lx->pos < lx->len) {
        if (lx->src[lx->pos] == '\n') break;
        lx->pos++;
    }
}

static int utf8_seqlen(unsigned char c) {
    if (c < 0x80) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

Token lexer_next(Lexer *lx) {
    Token tok;

    while (lx->pos < lx->len) {
        int c = (unsigned char)lx->src[lx->pos];

        if (c == '/' && lx->pos + 1 < lx->len &&
            lx->src[lx->pos + 1] == '/') {
            lx->pos += 2;
            skip_comment(lx);
            continue;
        }

        if (is_space(c)) {
            while (lx->pos < lx->len && is_space((unsigned char)lx->src[lx->pos]))
                lx->pos++;
            tok.kind = TOK_SPACE;
            tok.value = 0;
            return tok;
        }

        tok.kind = TOK_SYMBOL;
        int cp = decode_utf8((const unsigned char *)lx->src + lx->pos,
                             (int)(lx->len - lx->pos));
        int slen = utf8_seqlen((unsigned char)c);
        lx->pos += slen;
        tok.value = cp >= 0 ? cp : c;
        return tok;
    }

    tok.kind = TOK_EOF;
    tok.value = 0;
    return tok;
}