#!/usr/bin/env bash
# Descobre os .mf nas duas pastas e executa o parser real para cada entrada.
# Os programas e as expectativas opcionais de AST/posição estão em arquivos;
# não há lista de casos, conteúdo MorseLang ou quantidade esperada neste script.
set -euo pipefail

SUITE_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJETO_DIR=$(CDPATH= cd -- "$SUITE_DIR/.." && pwd)
PYTHON_PARSER=${PYTHON_PARSER:-"$PROJETO_DIR/.venv/bin/python"}
VALIDAS="$SUITE_DIR/entradas_validas"
INVALIDAS="$SUITE_DIR/entradas_invalidas"
RELATORIOS=${TMPDIR:-/tmp}
FILTRO='*'
LIMITE=${PARSER_TIMEOUT:-10}
DETALHADO=0

ajuda() {
    cat <<'USO'
Uso: ./testes_parser/orquestrador.sh [opções]
  --validas PASTA       Pasta de entradas sintaticamente válidas.
  --invalidas PASTA     Pasta de entradas sintaticamente inválidas.
  --filtro PADRAO       Seleciona caminhos relativos; ex.: '*precedencia*'.
  --relatorios PASTA    Cria uma execução nova nesta pasta (padrão: temporária).
  --timeout SEGUNDOS   Limite por caso (também definido por PARSER_TIMEOUT).
  --detalhado           Mostra também os casos aprovados.
  -h, --ajuda           Exibe esta ajuda.

Novos arquivos .mf são descobertos automaticamente, inclusive em subpastas.
Expectativas opcionais ficam no arquivo de mesmo nome terminado em .json.
Erros léxicos, exceções e timeouts sempre contam como falha, nunca como rejeição
sintática correta. Relatórios são preservados; entradas não são modificadas.
Retornos: 0 = todos passaram; 1 = falha em teste; 2 = falha de preparação/uso.
USO
}

# Opções parametrizam a execução, sem exigir edições no código do orquestrador.
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

# Resolve caminhos antes de executar qualquer comando no projeto.
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

# globstar faz a descoberta recursiva. Arrays preservam espaços nos nomes;
# nullglob evita interpretar um padrão sem correspondências como um arquivo.
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

# Gera o parser oficial uma única vez. Nenhuma gramática alternativa é usada.
if ! make --no-print-directory -C "$PROJETO_DIR" gen; then
    printf 'Falha ao preparar o parser.\n' >&2
    exit 2
fi
if ! "$PYTHON_PARSER" "$SUITE_DIR/verificar.py" preparar --timeout "$LIMITE"; then
    exit 2
fi
mkdir -p -- "$RELATORIOS"
EXECUCAO=$(mktemp -d "$RELATORIOS/morselang-parser.XXXXXX")
RESULTADOS="$EXECUCAO/resultados.jsonl"
: > "$RESULTADOS"

printf 'Casos descobertos: %d\nRelatórios: %s\n' "${#ARQUIVOS[@]}" "$EXECUCAO"
TOTAL=0
FALHAS=0
INICIO=$SECONDS

# O shell controla a execução de cada arquivo. O auxiliar só verifica o caso
# recebido, chama a API real e grava o resultado observado em JSON Lines.
# Uma exceção do parser jamais é tratada como sucesso de um caso inválido.
for indice in "${!ARQUIVOS[@]}"; do
    if "$PYTHON_PARSER" "$SUITE_DIR/verificar.py" caso \
        --arquivo "${ARQUIVOS[$indice]}" --classe "${CLASSES[$indice]}" \
        --nome "${NOMES[$indice]}" --timeout "$LIMITE" --resultados "$RESULTADOS"; then
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

# O resumo é calculado a partir dos resultados reais. A quantidade descoberta
# é conferida, para uma interrupção ou falha de registro não produzir falso OK.
if ! "$PYTHON_PARSER" "$SUITE_DIR/verificar.py" resumir \
    --resultados "$RESULTADOS" --total "$TOTAL" --duracao "$((SECONDS - INICIO))"; then
    exit 1
fi
[[ "$FALHAS" -eq 0 ]]
