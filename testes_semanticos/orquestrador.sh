#!/usr/bin/env bash
# Descobre os .mf do corpus semântico e executa a cadeia real para cada entrada.
# Não há lista fixa de casos, conteúdo MorseLang nem quantidade esperada aqui.
set -euo pipefail

SUITE_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJETO_DIR=$(CDPATH= cd -- "$SUITE_DIR/.." && pwd)
PYTHON_SEMANTICO=${PYTHON_SEMANTICO:-"$PROJETO_DIR/.venv/bin/python"}
VALIDAS="$SUITE_DIR/entradas_validas"
INVALIDAS="$SUITE_DIR/entradas_invalidas"
RELATORIOS=${TMPDIR:-/tmp}
FILTRO='*'
LIMITE=${SEMANTICO_TIMEOUT:-10}
DETALHADO=0

ajuda() {
    cat <<'USO'
Uso: ./testes_semanticos/orquestrador.sh [opções]
  --validas PASTA       Pasta de entradas semanticamente válidas.
  --invalidas PASTA     Pasta de entradas semanticamente inválidas.
  --filtro PADRAO       Seleciona caminhos relativos; ex.: '*tom*'.
  --relatorios PASTA    Cria uma execução nova nesta pasta (padrão: temporária).
  --timeout SEGUNDOS   Limite por caso (também definido por SEMANTICO_TIMEOUT).
  --detalhado           Mostra também os casos aprovados.
  -h, --ajuda           Exibe esta ajuda.

Cada entrada precisa passar pelo lexer e pelo parser. Entradas inválidas devem
falhar especificamente na análise semântica. Expectativas opcionais ficam no
arquivo de mesmo nome terminado em .json. Relatórios são preservados; entradas
não são modificadas.
Retornos: 0 = todos passaram; 1 = falha em teste; 2 = falha de preparação/uso.
USO
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --validas|--invalidas|--filtro|--relatorios|--timeout)
            if [[ $# -lt 2 || -z "$2" ]]; then
                printf 'Falta valor para %s.\n' "$1" >&2
                exit 2
            fi
            case "$1" in
                --validas) VALIDAS=$2 ;;
                --invalidas) INVALIDAS=$2 ;;
                --filtro) FILTRO=$2 ;;
                --relatorios) RELATORIOS=$2 ;;
                --timeout) LIMITE=$2 ;;
            esac
            shift 2
            ;;
        --detalhado) DETALHADO=1; shift ;;
        -h|--ajuda|--help) ajuda; exit 0 ;;
        *) printf 'Opção desconhecida: %s\n' "$1" >&2; exit 2 ;;
    esac
done

if [[ ! -d "$VALIDAS" || ! -d "$INVALIDAS" ]]; then
    printf 'As duas pastas de entradas devem existir.\n' >&2
    exit 2
fi
VALIDAS=$(CDPATH= cd -- "$VALIDAS" && pwd)
INVALIDAS=$(CDPATH= cd -- "$INVALIDAS" && pwd)
if [[ "$VALIDAS" == "$INVALIDAS" ]]; then
    printf 'As pastas válidas e inválidas devem ser diferentes.\n' >&2
    exit 2
fi

shopt -s globstar nullglob dotglob
declare -a ARQUIVOS=() CLASSES=() NOMES=()
for classe in validas invalidas; do
    if [[ "$classe" == validas ]]; then pasta=$VALIDAS; else pasta=$INVALIDAS; fi
    for arquivo in "$pasta"/**/*.mf; do
        [[ -f "$arquivo" ]] || continue
        relativo=${arquivo#"$pasta"/}
        [[ "$relativo" == $FILTRO ]] || continue
        ARQUIVOS+=("$arquivo")
        CLASSES+=("$classe")
        NOMES+=("$relativo")
    done
done
if [[ ${#ARQUIVOS[@]} -eq 0 ]]; then
    printf 'Nenhum arquivo .mf encontrado com o filtro informado.\n' >&2
    exit 2
fi

# O código ANTLR costuma já estar gerado. Só chama o gerador se for necessário,
# para que a cadeia semântica também funcione sem Java depois da preparação.
if [[ ! -f "$PROJETO_DIR/gerado/MorseLangParser.py" ]]; then
    if ! make --no-print-directory -C "$PROJETO_DIR" gen; then
        printf 'Falha ao preparar o parser para a cadeia semântica.\n' >&2
        exit 2
    fi
fi

mkdir -p -- "$RELATORIOS"
EXECUCAO=$(mktemp -d "$RELATORIOS/morselang-semantico.XXXXXX")
RESULTADOS="$EXECUCAO/resultados.jsonl"
: > "$RESULTADOS"

printf 'Casos semânticos descobertos: %d\nRelatórios: %s\n' \
    "${#ARQUIVOS[@]}" "$EXECUCAO"
TOTAL=0
FALHAS=0
INICIO=$SECONDS

for indice in "${!ARQUIVOS[@]}"; do
    if "$PYTHON_SEMANTICO" "$SUITE_DIR/verificar.py" caso \
        --arquivo "${ARQUIVOS[$indice]}" --classe "${CLASSES[$indice]}" \
        --nome "${NOMES[$indice]}" --timeout "$LIMITE" \
        --resultados "$RESULTADOS"; then
        if [[ "$DETALHADO" -eq 1 ]]; then
            printf '[OK] %s/%s\n' "${CLASSES[$indice]}" "${NOMES[$indice]}"
        fi
    else
        retorno=$?
        FALHAS=$((FALHAS + 1))
        printf '[FALHA] %s/%s (retorno %d)\n' \
            "${CLASSES[$indice]}" "${NOMES[$indice]}" "$retorno" >&2
    fi
    TOTAL=$((TOTAL + 1))
done

if ! "$PYTHON_SEMANTICO" "$SUITE_DIR/verificar.py" resumir \
    --resultados "$RESULTADOS" --total "$TOTAL" \
    --duracao "$((SECONDS - INICIO))"; then
    exit 1
fi
[[ "$FALHAS" -eq 0 ]]
