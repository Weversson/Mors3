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

`mensagem` define um texto, `tom` e `velocidade` definem parâmetros do áudio, e `emitir` indica o texto que será convertido. Na E2, o programa é analisado apenas em tokens; ele ainda não é executado.

## 2. Instalação e execução

Requisitos: Python 3.10 ou superior, Java 11 ou superior, `make` e `curl`. O primeiro `make` precisa de acesso à internet para obter o ANTLR e o runtime Python. O gerador e o runtime estão fixados na versão **ANTLR 4.13.2**.

```sh
make
.venv/bin/python src/lexico.py exemplos/ola.mf
```

O analisador imprime tipo, texto, linha e coluna de cada token, seguidos do total. Para conferir um erro léxico:

```sh
.venv/bin/python src/lexico.py exemplos/invalidos/caractere_invalido.mf
```

Depois da instalação, `./gerar.sh` regenera o lexer ANTLR. `make run` analisa `exemplos/ola.mf`; use `make run INPUT=exemplos/eco.mf` para outro arquivo.

## 3. Fase atual

Esta entrega corresponde à **E2: especificação e analisador léxico**. A gramática [gramatica/MorseLang.g4](gramatica/MorseLang.g4) contém apenas regras de lexer. A análise sintática e a árvore serão tratadas na E3; a análise semântica e a execução, incluindo os arquivos `.morse` e `.wav`, serão tratadas na E4. `tests/test_viabilidade_e3.py` gera temporariamente um parser ANTLR que reutiliza os tokens atuais e aceita os três exemplos válidos.

O antigo `mfcc.py`, `grammar/Morse.g4`, `legacy_c/` e os módulos de geração em `src/` formam protótipos de tradução de texto livre. Eles não reconhecem a sintaxe de MorseLang e não são apresentados como implementação da E2. `make prototype` executa o protótipo Python, e seus testes foram preservados.

## 4. Testes

```sh
make test
```

Os testes cobrem as categorias de token, comentários e espaços descartados, linha e coluna dos tokens, os três exemplos válidos, os três inválidos, a compatibilidade com um parser ANTLR e o funcionamento anterior do protótipo.

## 5. Arquivos principais

```text
docs/especificacao.md       definição da linguagem
gramatica/MorseLang.g4       gramática ANTLR só de lexer
gerar.sh                    regenera o lexer em gerado/
src/lexico.py               lista tokens ou aponta erro léxico
exemplos/                   três programas válidos
exemplos/invalidos/         três programas com erro léxico
DIARIO.md                   registro das sessões de trabalho
```

`gerado/` é produzido pelo ANTLR e ignorado pelo Git.
