# MorseLang

## 1. Linguagem e exemplo

MorseLang é uma linguagem pequena para compor mensagens destinadas à conversão em código Morse. Sua definição está em [docs/especificacao.md](docs/especificacao.md).

```text
// Uma mensagem curta para teste.
mensagem alerta = "SOS";
tom 600.0;
velocidade 20;
emitir (alerta + " AJUDA") * 2;
```

`mensagem` define um texto, `tom` e `velocidade` definem parâmetros do áudio, e `emitir` indica o texto que será convertido. A implementação atual realiza as análises léxica e sintática e constrói as árvores do programa. A execução e a conversão da nova linguagem para Morse e áudio pertencem à E4.

## 2. Instalação e execução

Requisitos: Python 3.10 ou superior, Java 11 ou superior, `make` e `curl`. O primeiro `make` precisa de acesso à internet para obter o ANTLR e o runtime Python. O gerador e o runtime estão fixados na versão **ANTLR 4.13.2**.

```sh
make
make sintatico
make sintatico INPUT=exemplos/eco.mf
```

O analisador sintático informa se o programa tem uma estrutura válida. Para visualizar as árvores:

```sh
# Árvore concreta: regras da gramática, tokens, pontuação e EOF.
.venv/bin/python src/sintatico.py exemplos/ola.mf --arvore

# AST: comandos e expressões, com tipos dos nós e posições na fonte.
.venv/bin/python src/sintatico.py exemplos/ola.mf --ast

# Alternativa usando o Makefile.
make sintatico INPUT=exemplos/precedencia.mf ARGS=--arvore
```

`--ast` escreve somente JSON em stdout, permitindo redirecionamento para um arquivo. `--arvore` e `--ast` são alternativas de saída. A execução como módulo também funciona: `.venv/bin/python -m src.sintatico exemplos/ola.mf`.

Para conferir um erro sintático e um erro léxico:

```sh
.venv/bin/python src/sintatico.py exemplos/invalidos/sintaticos/sem_ponto_virgula.mf
.venv/bin/python src/sintatico.py exemplos/invalidos/caractere_invalido.mf
```

Os erros são enviados a stderr com linha e coluna contadas a partir de 1. A análise para no primeiro erro da etapa; o arquivo inteiro passa pelo lexer antes do parser. Uma falha retorna código 1 e não imprime uma árvore parcial. Opções de linha de comando incorretas retornam código 2; sucesso retorna 0.

O analisador da E2 continua disponível: `.venv/bin/python src/lexico.py exemplos/ola.mf` lista tipo, texto, linha e coluna de cada token. `make run` mantém essa análise léxica; use `make run INPUT=exemplos/eco.mf` para outro arquivo. Depois da instalação, `./gerar.sh` regenera o lexer, o parser e o visitante ANTLR em `gerado/`.

## 3. Fase atual

Esta etapa implementa a **E3: analisador sintático e árvores**, preservando o lexer da E2 em [gramatica/MorseLang.g4](gramatica/MorseLang.g4). O parser permanente está em [gramatica/MorseLangParser.g4](gramatica/MorseLangParser.g4) e reutiliza os mesmos tokens por meio de `tokenVocab=MorseLang`.

O parser exige pelo menos um `emitir`, aceita mensagens e configurações antes das emissões e permite cada configuração no máximo uma vez. `tom` e `velocidade` podem aparecer em qualquer ordem, intercalados com declarações. A repetição tem precedência sobre a concatenação; ambos os operadores são associados à esquerda. Parênteses alteram o agrupamento, e `EOF` garante que a fonte inteira seja consumida.

A árvore concreta mostra a estrutura reconhecida pelo ANTLR. O visitante em `src/construir_ast.py` produz uma AST própria da MorseLang, preservando a ordem dos comandos e os agrupamentos das expressões. Veja a divisão entre sintaxe e semântica e um exemplo da AST na [especificação](docs/especificacao.md#8-análise-sintática-e-árvores-e3).

Nomes não declarados ou redefinidos, valores numéricos fora dos limites e caracteres sem código Morse ainda dependem da análise semântica da E4. Por exemplo, `emitir ausente;` e `emitir "A" * 0;` têm sintaxe reconhecida, mas isso não significa que sejam programas semanticamente válidos. O parser não atribui valores padrão, não expande repetições e não gera `.morse` ou `.wav`.

O antigo `mfcc.py`, `grammar/Morse.g4`, `legacy_c/` e os módulos de geração em `src/` formam protótipos de tradução de texto livre. Eles não reconhecem os comandos de MorseLang. `make prototype` executa o protótipo Python, e seus testes foram preservados.

## 4. Testes

```sh
make test
```

Os testes cobrem tokens, comentários, posições, exemplos válidos e inválidos, regras de ordenação dos comandos, unicidade das configurações, precedência, associatividade, parênteses aninhados, AST, mensagens de erro e execução da CLI. Também verificam que erros léxicos não sejam ignorados pelo parser e que nenhuma saída de áudio seja produzida nesta etapa. Os testes anteriores do protótipo permanecem na suíte. O teste temporário de viabilidade da E3 foi substituído pelos testes do parser permanente em `tests/test_sintatico.py`.

Para executar somente o conjunto de entradas do parser, separado em `testes_parser/entradas_validas/` e `testes_parser/entradas_invalidas/`:

```sh
./testes_parser/orquestrador.sh
```

O orquestrador descobre os arquivos automaticamente, compara as expectativas externas de AST quando presentes e salva os resultados reais em JSON. Novos arquivos `.mf` entram na suíte sem editar o script. Consulte [testes_parser/README.md](testes_parser/README.md) para filtros, relatórios e cobertura.

## 5. Arquivos principais

```text
docs/especificacao.md           definição da linguagem e limites de cada etapa
gramatica/MorseLang.g4           gramática do lexer E2
gramatica/MorseLangParser.g4     gramática do parser E3
gerar.sh                        gera lexer, parser e visitante em gerado/
src/lexico.py                   análise léxica e listagem de tokens
src/sintatico.py                análise sintática e CLI
src/ast_morselang.py             nós da AST e representação em JSON
src/construir_ast.py             visitante que constrói a AST
tests/test_sintatico.py          testes do parser, árvores e CLI
exemplos/                       cinco programas sintaticamente válidos
exemplos/invalidos/              três programas com erro léxico
exemplos/invalidos/sintaticos/    seis programas com erro sintático
DIARIO.md                       registro das sessões de trabalho
```

`gerado/` é produzido pelo ANTLR e ignorado pelo Git.
