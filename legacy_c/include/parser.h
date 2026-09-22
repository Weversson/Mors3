#ifndef MORSE_PARSER_H
#define MORSE_PARSER_H

#include "ast.h"
#include <stddef.h>

Document *parse_source(const char *src, size_t len, size_t *warnings);

#endif