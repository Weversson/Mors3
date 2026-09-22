#!/usr/bin/env sh
set -eu

PROJETO_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ANTLR_VERSION=${ANTLR_VERSION:-4.13.2}

mkdir -p "$PROJETO_DIR/gerado"
touch "$PROJETO_DIR/gerado/__init__.py"

cd "$PROJETO_DIR/gramatica"
java -jar "../tools/antlr-$ANTLR_VERSION-complete.jar" \
    -Dlanguage=Python3 -o ../gerado MorseLang.g4
