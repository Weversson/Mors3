#!/usr/bin/env bash
# Demonstração da MorseLang: análise léxica (E2) e sintática (E3).
#
# Uso: ./demonstrar.sh           executa todos os exemplos sem pausas.
#      ./demonstrar.sh --pausar  espera Enter depois de cada exemplo.
#      ./demonstrar.sh --ajuda   mostra as instruções de uso.
#
# Cada caso mostra a entrada, o comando executado, a saída e o resultado
# esperado. Os erros dos exemplos inválidos são intencionais: a demonstração
# continua e só termina com falha se algum resultado for diferente do esperado.
#
# Requisitos: Bash, Python 3.10+, Java 11+, make e curl. O comando make gen
# prepara as dependências e gera o código ANTLR. Na primeira instalação,
# pode precisar de internet para baixar o gerador e o runtime Python.
#
# Os exemplos existentes são apenas lidos. As entradas adicionais ficam em
# uma pasta temporária, removida ao sair. Esta demonstração não gera áudio:
# a execução de programas MorseLang pertence à futura etapa E4.

set -euo pipefail

# Localiza o projeto mesmo quando este script é chamado de outra pasta.
PROJETO_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON_DEMO="$PROJETO_DIR/.venv/bin/python"
PAUSAR=0
TOTAL=0
FALHAS=0

# As opções são processadas antes da preparação, para --ajuda não executar nada.
for argumento in "$@"; do
    case "$argumento" in
        --pausar) PAUSAR=1 ;;
        -h|--ajuda|--help)
            cat <<'AJUDA'
Uso: ./demonstrar.sh [--pausar]

Mostra entradas válidas e inválidas, tokens, árvore ANTLR e AST em JSON.
--pausar aguarda Enter depois de cada caso, facilitando uma apresentação.
Sem essa opção, todos os casos são executados automaticamente.

Retorno 0: todos os resultados corresponderam ao esperado.
Retorno 1: houve falha de preparação ou resultado inesperado.
Retorno 2: opção incorreta ou pausa solicitada sem terminal interativo.
AJUDA
            exit 0
            ;;
        *)
            printf 'Opção desconhecida: %s. Use --ajuda.\n' "$argumento" >&2
            exit 2
            ;;
    esac
done

# A pausa é opcional; a execução padrão também funciona com saída redirecionada.
if [[ "$PAUSAR" -eq 1 && ! -t 0 ]]; then
    printf 'A opção --pausar precisa de um terminal interativo.\n' >&2
    exit 2
fi

cd -- "$PROJETO_DIR"
printf 'MorseLang: demonstração do lexer e do parser com ANTLR\n'
printf 'O lexer reconhece tokens; o parser verifica a estrutura e produz árvores.\n'
printf 'A análise semântica e a execução das mensagens ainda pertencem à E4.\n\n'

# Usa a preparação oficial do projeto e regenera lexer, parser e visitante.
# Uma falha aqui é um problema de preparação, não um erro esperado dos exemplos.
if ! make --no-print-directory gen; then
    printf 'Não foi possível preparar o projeto. Confira o erro acima.\n' >&2
    exit 1
fi

# Somente esta pasta criada pelo script será apagada ao encerrar.
DEMO_DIR=$(mktemp -d "${TMPDIR:-/tmp}/morselang-demo.XXXXXX")
trap 'rm -rf -- "$DEMO_DIR"' EXIT

# Here-documents com delimitadores entre aspas preservam literalmente o código
# MorseLang, sem expansão de variáveis ou execução de comandos pelo shell.
cat > "$DEMO_DIR/simples.mf" <<'MORSE'
// Mensagem literal repetida duas vezes.
emitir "SOS" * 2;
MORSE

cat > "$DEMO_DIR/operador_fora_de_lugar.mf" <<'MORSE'
// Todos os tokens existem, mas a organização deles é inválida.
emitir * "SOS";
MORSE

cat > "$DEMO_DIR/nome_nao_declarado.mf" <<'MORSE'
// A estrutura está correta; a verificação do nome será feita na E4.
emitir ausente;
MORSE

# Executa um caso real, sem simular resultados e sem usar eval.
# Argumentos: título, explicação, arquivo, analisador, código de saída esperado,
# trecho esperado na saída e, opcionalmente, --arvore ou --ast.
demonstrar_caso() {
    local titulo=$1 explicacao=$2 arquivo=$3 analisador=$4
    local esperado=$5 trecho=$6
    shift 6
    local saida retorno
    local -a comando=("$PYTHON_DEMO" "src/$analisador.py" "$arquivo" "$@")

    TOTAL=$((TOTAL + 1))
    printf '\nCaso %d: %s\n' "$TOTAL" "$titulo"
    printf '%s\n' "$explicacao"
    printf 'Entrada (%s):\n' "$(basename -- "$arquivo")"
    # Numera as linhas para facilitar a comparação com as posições dos erros.
    cat -n -- "$arquivo"
    printf '\nComando:'
    printf ' %q' "${comando[@]}"
    printf '\nSaída:\n'

    # O if permite observar erros esperados sem interromper o set -e.
    # stdout e stderr são reunidos para manter a mensagem perto do seu exemplo.
    if saida=$("${comando[@]}" 2>&1); then
        retorno=0
    else
        retorno=$?
    fi
    printf '%s\n' "$saida"
    printf 'Código de saída esperado: %s | obtido: %s\n' "$esperado" "$retorno"

    # Confere também a categoria da resposta. Assim, uma falha de importação
    # não será confundida com a rejeição léxica ou sintática que queríamos mostrar.
    if [[ "$retorno" -eq "$esperado" && "$saida" == *"$trecho"* ]]; then
        printf '[OK] Resultado esperado confirmado.\n'
    else
        FALHAS=$((FALHAS + 1))
        printf '[FALHA] Era esperado encontrar: %s\n' "$trecho"
    fi

    if [[ "$PAUSAR" -eq 1 ]]; then
        printf '\nPressione Enter para continuar... '
        if ! IFS= read -r; then
            printf '\nEntrada encerrada; demonstração interrompida.\n' >&2
            exit 1
        fi
    fi
}

# 1. A mesma entrada válida passa pelas duas etapas.
# O lexer lista tokens; o parser reconhece um comando completo.
demonstrar_caso 'Lexer: entrada válida' \
    'Observe EMITIR, TEXTO, VEZES, INTEIRO e PONTO_VIRGULA. O comentário é descartado.' \
    "$DEMO_DIR/simples.mf" lexico 0 'tokens reconhecidos'

demonstrar_caso 'Parser: entrada válida' \
    'Os tokens formam uma emissão com repetição de texto.' \
    "$DEMO_DIR/simples.mf" sintatico 0 'Programa sintaticamente válido'

# 2. Mostra as duas representações da estrutura: árvore concreta e abstrata.
# A árvore ANTLR mantém regras e pontuação; a AST representa comandos e expressões.
demonstrar_caso 'Programa completo e árvore ANTLR' \
    'Declara mensagem, configura tom e velocidade e emite uma expressão com parênteses.' \
    exemplos/ola.mf sintatico 0 '(programa' --arvore

demonstrar_caso 'Árvore sintática abstrata em JSON' \
    'Na AST, Emissao contém Repeticao, que contém o Texto SOS e a quantidade 2.' \
    "$DEMO_DIR/simples.mf" sintatico 0 '"tipo": "Programa"' --ast

# 3. Estes exemplos mostram as demais formas válidas previstas na linguagem.
demonstrar_caso 'Referência a uma mensagem' \
    'A expressão usa o nome eco e aplica o operador de repetição.' \
    exemplos/eco.mf sintatico 0 'Programa sintaticamente válido'

demonstrar_caso 'Configurações e concatenação' \
    'Tom real, velocidade inteira e concatenação de uma referência com texto.' \
    exemplos/aviso.mf sintatico 0 'Programa sintaticamente válido'

demonstrar_caso 'Várias emissões' \
    'As configurações podem aparecer em ambas as ordens e entre declarações, antes das emissões.' \
    exemplos/multiplas_emissoes.mf sintatico 0 'Programa sintaticamente válido'

demonstrar_caso 'Precedência e parênteses' \
    'Compare as duas ASTs: A + B * 2 concatena com uma repetição; (A + B) * 2 repete a concatenação.' \
    exemplos/precedencia.mf sintatico 0 '"tipo": "Programa"' --ast

# 4. Erros léxicos: os caracteres não formam os tokens permitidos.
# Esses casos devem retornar 1, com a categoria "erro léxico" e a posição.
demonstrar_caso 'Erro léxico: caractere inválido' \
    'O caractere @ fora de um literal de texto não pertence à linguagem.' \
    exemplos/invalidos/caractere_invalido.mf lexico 1 'erro léxico:'

demonstrar_caso 'Erro léxico: texto sem fechar' \
    'O literal começou com aspas, mas não tem as aspas de fechamento.' \
    exemplos/invalidos/texto_sem_fechar.mf lexico 1 'erro léxico:'

demonstrar_caso 'Erro léxico: número malformado' \
    '600..5 não é um literal numérico válido: há dois pontos consecutivos.' \
    exemplos/invalidos/numero_malformado.mf lexico 1 'erro léxico:'

demonstrar_caso 'O parser também interrompe em erro léxico' \
    'A CLI sintática executa o lexer primeiro; o caractere inválido não é ignorado.' \
    exemplos/invalidos/caractere_invalido.mf sintatico 1 'erro léxico:'

# 5. Diferença central entre as etapas: tokens válidos podem formar um programa
# sintaticamente inválido. Observe a MESMA entrada nos próximos dois casos.
demonstrar_caso 'Lexer aceita os tokens fora de ordem' \
    'emitir, *, "SOS" e ; são tokens reconhecidos individualmente.' \
    "$DEMO_DIR/operador_fora_de_lugar.mf" lexico 0 'tokens reconhecidos'

demonstrar_caso 'Parser rejeita os tokens fora de ordem' \
    'Depois de emitir deve começar uma expressão; o operador * não pode aparecer sozinho.' \
    "$DEMO_DIR/operador_fora_de_lugar.mf" sintatico 1 'erro sintático:'

# 6. Outros erros sintáticos: a gramática exige pontuação, operandos e uma
# organização específica para as declarações, configurações e emissões.
demonstrar_caso 'Erro sintático: falta ponto e vírgula' \
    'Todo comando deve terminar com ;.' \
    exemplos/invalidos/sintaticos/sem_ponto_virgula.mf sintatico 1 'erro sintático:'

demonstrar_caso 'Erro sintático: parêntese aberto' \
    'O agrupamento iniciado com ( precisa terminar com ).' \
    exemplos/invalidos/sintaticos/parentese_aberto.mf sintatico 1 'erro sintático:'

demonstrar_caso 'Erro sintático: ausência de emissão' \
    'Declarar uma mensagem não basta: o programa precisa ter pelo menos um emitir.' \
    exemplos/invalidos/sintaticos/sem_emitir.mf sintatico 1 'erro sintático:'

demonstrar_caso 'Erro sintático: configuração repetida' \
    'O tom pode ser configurado no máximo uma vez por programa.' \
    exemplos/invalidos/sintaticos/configuracao_repetida.mf sintatico 1 'erro sintático:'

demonstrar_caso 'Erro sintático: declaração depois da emissão' \
    'Depois do primeiro emitir, somente outras emissões são permitidas.' \
    exemplos/invalidos/sintaticos/declaracao_apos_emitir.mf sintatico 1 'erro sintático:'

demonstrar_caso 'Erro sintático: repetição com número real' \
    '2.5 é um token REAL válido, mas o lado direito de * exige um INTEIRO.' \
    exemplos/invalidos/sintaticos/repeticao_real.mf sintatico 1 'erro sintático:'

# 7. Explicita o limite da etapa atual, sem apresentar sintaxe aceita como
# prova de validade semântica ou de execução da mensagem.
demonstrar_caso 'Limite da E3: nome ainda não declarado' \
    'A sintaxe é aceita. Detectar que ausente não foi declarado será responsabilidade da E4.' \
    "$DEMO_DIR/nome_nao_declarado.mf" sintatico 0 'Programa sintaticamente válido'

# Um erro intencional que foi corretamente rejeitado conta como demonstração
# bem-sucedida. Somente resultados inesperados tornam a saída final diferente de 0.
printf '\nDemonstração concluída: %d de %d resultados corresponderam ao esperado.\n' \
    "$((TOTAL - FALHAS))" "$TOTAL"
printf 'Lexer: reconhecimento de tokens. Parser: organização dos tokens e construção das árvores.\n'
printf 'Nenhum programa MorseLang foi executado para produzir Morse ou áudio.\n'
if [[ "$FALHAS" -ne 0 ]]; then
    printf 'Foram encontrados %d resultados inesperados.\n' "$FALHAS" >&2
    exit 1
fi
