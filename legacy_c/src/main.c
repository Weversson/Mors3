#include "codegen.h"
#include "parser.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void usage(const char *prog) {
    fprintf(stderr,
            "Uso: %s [-o <base>] [--freq <hz>] [--wpm <num>] <arquivo.mf>\n"
            "Compila um arquivo de texto para código Morse.\n\n"
            "Opções:\n"
            "  -o <base>      caminho base de saída (sem extensão)\n"
            "  --freq <hz>    frequência do tom em Hz (padrão: 600)\n"
            "  --wpm <num>    velocidade em palavras/minuto (padrão: 20)\n"
            "  -h, --help     mostra esta ajuda\n",
            prog);
}

static char *read_file(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    long sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return NULL;
    }
    if (fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return NULL;
    }
    char *buf = malloc((size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[rd] = '\0';
    if (out_len) *out_len = rd;
    return buf;
}

int main(int argc, char **argv) {
    const char *input = NULL;
    const char *out_base = NULL;
    int freq = 600;
    int wpm = 20;

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "-h") == 0 || strcmp(a, "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else if (strcmp(a, "-o") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "erro: -o requer um argumento\n");
                return 1;
            }
            out_base = argv[++i];
        } else if (strcmp(a, "--freq") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "erro: --freq requer um argumento\n");
                return 1;
            }
            freq = atoi(argv[++i]);
        } else if (strcmp(a, "--wpm") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "erro: --wpm requer um argumento\n");
                return 1;
            }
            wpm = atoi(argv[++i]);
        } else if (a[0] == '-' && a[1] != '\0') {
            fprintf(stderr, "erro: opção desconhecida '%s'\n", a);
            return 1;
        } else {
            if (input) {
                fprintf(stderr, "erro: apenas um arquivo de entrada é permitido\n");
                return 1;
            }
            input = a;
        }
    }

    if (!input) {
        usage(argv[0]);
        return 1;
    }
    if (wpm <= 0) {
        fprintf(stderr, "erro: --wpm deve ser um inteiro positivo\n");
        return 1;
    }
    if (freq < 100 || freq > 20000) {
        fprintf(stderr, "erro: --freq deve estar entre 100 e 20000\n");
        return 1;
    }

    char basebuf[2048];
    const char *base = out_base;
    if (!base) {
        snprintf(basebuf, sizeof basebuf, "%s", input);
        char *dot = strrchr(basebuf, '.');
        if (dot) *dot = '\0';
        base = basebuf;
    }

    size_t len = 0;
    char *src = read_file(input, &len);
    if (!src) {
        fprintf(stderr, "erro: não foi possível ler '%s'\n", input);
        return 1;
    }

    size_t warnings = 0;
    Document *doc = parse_source(src, len, &warnings);
    free(src);
    if (!doc) {
        fprintf(stderr, "erro: falha interna ao compilar\n");
        return 1;
    }

    if (warnings > 0)
        fprintf(stderr, "aviso: %zu caractere(s) sem código Morse foram ignorados\n",
                warnings);

    if (doc->len == 0) {
        fprintf(stderr, "erro: nenhum texto compilável encontrado\n");
        doc_free(doc);
        return 1;
    }

    CodegenOptions opt;
    opt.freq = freq;
    opt.wpm = wpm;
    opt.base = base;

    if (codegen_emit(doc, &opt) != 0) {
        fprintf(stderr, "erro: falha ao gerar os arquivos de saída\n");
        doc_free(doc);
        return 1;
    }

    printf("OK: gerado %s.morse (texto) e %s.wav (áudio)\n", base, base);
    doc_free(doc);
    return 0;
}