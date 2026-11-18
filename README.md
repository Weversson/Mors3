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

`mensagem` define um texto, `tom` e `velocidade` definem parâmetros do áudio, e `emitir` indica o texto que será convertido. A implementação realiza as análises léxica, sintática e semântica, constrói as árvores do programa, expande as emissões em uma timeline, reproduz essa timeline no navegador e grava as saídas `.morse` e `.wav`.

## 2. Instalação e execução

Requisitos: Python 3.10 ou superior, Java 11 ou superior, `make` e `curl`. O primeiro `make` precisa de acesso à internet para obter o ANTLR e o runtime Python. O gerador e o runtime estão fixados na versão **ANTLR 4.13.2**.

```sh
make
make sintatico
make sintatico INPUT=exemplos/eco.mf
make semantico
make semantico INPUT=exemplos/eco.mf
make timeline
make timeline INPUT=exemplos/ola.mf
make exportar
make visual
```

`make exportar` grava `.morse` e `.wav` ao lado da entrada. `make visual` sobe a interface web local descrita adiante; ela também pode ser iniciada com `.venv/bin/python -m src.visual`.

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

O analisador semântico executa as etapas léxica, sintática e semântica sem gerar arquivos de saída:

```sh
make semantico
make semantico INPUT=exemplos/ola.mf
.venv/bin/python src/semantico.py exemplos/ola.mf
.venv/bin/python -m src.semantico exemplos/ola.mf
.venv/bin/python -m src.analise_semantica exemplos/ola.mf
```

No sucesso, a CLI informa a quantidade de emissões e as configurações efetivas, incluindo os padrões. Uma falha semântica imprime `erro semântico:` em stderr e retorna 1. A API pode ser usada diretamente:

```python
from src.semantico import analisar_fonte

resultado = analisar_fonte('tom 700; emitir "SOS" * 2;')
print(resultado.tom, resultado.velocidade, resultado.quantidade_emissoes)
```

A etapa de execução expande as emissões em uma linha do tempo de tons e silêncios, sem gerar arquivos. O padrão PARIS define a duração de cada elemento a partir da velocidade: ponto, traço, intervalos entre símbolos, caracteres e palavras.

```sh
.venv/bin/python -m src.execucao exemplos/ola.mf
.venv/bin/python -m src.execucao exemplos/ola.mf --resumo
.venv/bin/python -m src.execucao exemplos/ola.mf --limite 10000
```

Por padrão a CLI imprime a timeline completa em JSON, com configurações efetivas, texto expandido, duração total e um evento por tom ou silêncio. `--resumo` mostra apenas as configurações e as contagens. `--limite` protege interfaces interativas contra expansões muito grandes. A API equivalente é:

```python
from src.execucao import expandir
from src.semantico import analisar_fonte

timeline = expandir(analisar_fonte('emitir "SOS";'))
print(timeline.texto, timeline.duracao_total_ms, len(timeline.eventos))
```

A geração grava as saídas finais a partir da mesma timeline, sem recriar os tempos:

```sh
make exportar
make exportar INPUT=exemplos/eco.mf
.venv/bin/python -m src.geracao exemplos/ola.mf
.venv/bin/python -m src.geracao exemplos/ola.mf --morse /tmp/msg.morse --wav /tmp/msg.wav
.venv/bin/python -m src.geracao exemplos/ola.mf --taxa 22050
```

Sem opções de caminho, os arquivos recebem o mesmo nome base da entrada. Informando apenas `--morse` ou apenas `--wav`, somente aquele arquivo é gravado. O `.morse` usa uma linha por `emitir`, com caracteres separados por espaço e palavras por ` / `. O `.wav` é mono, 16 bits e, por padrão, 44100 Hz; o tom e a duração vêm da timeline. A API Python correspondente é:

```python
from src.geracao import gerar_morse, gerar_wav
from src.semantico import analisar_fonte
from src.execucao import expandir

timeline = expandir(analisar_fonte('emitir "SOS";'))
texto = gerar_morse(timeline)
audio = gerar_wav(timeline)  # bytes de um arquivo WAV completo
```

A visualização web local reúne as quatro etapas, reproduz a timeline com a Web Audio API e permite baixar as saídas:

```sh
make visual
make visual PORTA=8080
.venv/bin/python -m src.visual --abrir
```

O servidor escuta em `127.0.0.1:8000` por padrão e serve a página em `/`. A cada edição do código, a página envia a fonte para `POST /api/analisar` e atualiza tokens, símbolos, AST, métricas e a faixa de tons e silêncios. O botão **Reproduzir** agenda os eventos na Web Audio API, destacando o evento e o ponto atuais em sincronia com o áudio. Os botões **Baixar .morse** e **Baixar .wav** usam `POST /api/exportar`, que devolve o arquivo com cabeçalho de anexo; o corpo envia `{"fonte": "...", "formato": "morse"|"wav"}`. `GET /api/saude` (ou `GET /health`) informa o serviço e o limite de expansão configurado.

Erros de análise são respostas HTTP 200 com `ok: false` e o campo `etapa` (`lexico`, `sintatico`, `semantico` ou `execucao`), permitindo mostrar tokens e AST parciais. Requisições malformadas retornam 4xx. O corpo é limitado a 1 MB e a expansão padrão a 10.000 caracteres; `--limite` ajusta esse teto. O servidor não deve ser exposto à rede sem revisão das proteções.

O analisador da E2 continua disponível: `.venv/bin/python src/lexico.py exemplos/ola.mf` lista tipo, texto, linha e coluna de cada token. A implementação vive no pacote [src/analise_lexica](src/analise_lexica), com modelo de token, diagnóstico, analisador e CLI separados. O módulo `src/lexico.py` permanece como fachada compatível e pode ser executado também com `python -m src.analise_lexica`. `make lexico` e `make run` executam essa análise; use `make run INPUT=exemplos/eco.mf` para outro arquivo. Depois da instalação, `./gerar.sh` regenera o lexer, o parser e o visitante ANTLR em `gerado/`.

A API lexical pode ser usada diretamente:

```python
from src.analise_lexica import analisar, iterar_tokens

tokens = analisar('emitir "SOS";')       # lista completa
for token in iterar_tokens('tom 600;'):  # geração sob demanda
    print(token.tipo, token.texto, token.linha, token.coluna)
```

## 3. Fase atual

Esta etapa implementa a **E4: análise semântica, timeline de execução, geração de arquivos e visualização web**, preservando o lexer da E2 em [gramatica/MorseLang.g4](gramatica/MorseLang.g4) e o parser da E3 em [gramatica/MorseLangParser.g4](gramatica/MorseLangParser.g4). As implementações modulares ficam em [src/analise_lexica](src/analise_lexica), [src/analise_semantica](src/analise_semantica), [src/execucao](src/execucao), [src/geracao](src/geracao) e [src/visual](src/visual); a fachada e a CLI semântica estão em `src/semantico.py`.

O parser exige pelo menos um `emitir`, aceita mensagens e configurações antes das emissões e permite cada configuração no máximo uma vez. `tom` e `velocidade` podem aparecer em qualquer ordem, intercalados com declarações. A repetição tem precedência sobre a concatenação; ambos os operadores são associados à esquerda. Parênteses alteram o agrupamento, e `EOF` garante que a fonte inteira seja consumida.

A árvore concreta mostra a estrutura reconhecida pelo ANTLR. O visitante em `src/construir_ast.py` produz uma AST própria da MorseLang, preservando a ordem dos comandos e os agrupamentos das expressões. Veja a divisão entre sintaxe e semântica e um exemplo da AST na [especificação](docs/especificacao.md#9-análise-sintática-e-árvores-e3).

Depois do parser, o analisador semântico percorre a AST e exige nomes declarados antes do uso e sem redefinição, repetição com inteiro positivo, tom entre 100 e 20000 Hz, velocidade com inteiro positivo e caracteres de todo texto com representação na tabela Morse fixa. Espaços separam palavras, acentos são normalizados e texto vazio é aceito. `tom` e `velocidade` recebem os padrões de 600 Hz e 20 palavras por minuto, e o resultado informa as configurações efetivas. A análise semântica para no primeiro erro e não expande repetições; a etapa de execução faz a expansão em uma timeline, e a geração converte essa timeline nos arquivos finais.

Assim, `emitir ausente;`, `emitir "A" * 0;`, `tom 0;` e `emitir "😀";` têm sintaxe reconhecida, mas são rejeitados pela análise semântica. O corpus `exemplos/invalidos/semanticos/` cobre cada uma dessas regras. A timeline de execução está implementada, a visualização web reproduz os tons e silêncios com Web Audio, e os geradores gravam `.morse` e `.wav` a partir da mesma timeline.

O antigo `mfcc.py`, `grammar/Morse.g4`, `legacy_c/` e os módulos de geração em `src/` formam protótipos de tradução de texto livre. Eles não reconhecem os comandos de MorseLang. `make prototype` executa o protótipo Python, e seus testes foram preservados.

## 4. Testes

```sh
make test
```

Os testes do lexer cobrem todas as categorias de token, limites entre palavras-chave e identificadores, literais, comentários, espaços, posições em LF/CRLF, Unicode, primeiro erro, exemplos válidos e inválidos e a CLI. Os testes do parser cobrem a ordenação dos comandos, unicidade das configurações, precedência, associatividade, parênteses aninhados, AST, mensagens de erro e execução da CLI. Os testes semânticos cobrem resolução e redefinição de nomes, repetição positiva, limites de tom, velocidade positiva, caracteres com representação Morse, padrões, posições, primeiro erro, corpus inválido e as CLIs direta e modular. Os testes de execução cobrem a unidade PARIS, concatenação, repetição, referências, normalização de espaços, separação entre emissões, durações, contiguidade dos eventos, limite de expansão e a CLI. Os testes de geração cobrem o formato do `.morse`, uma linha por emissão, normalização de acentos, o cabeçalho e os samples do WAV, a frequência do tom, os silêncios, opções inválidas e a CLI. Os testes da visualização cobrem o contrato JSON, erros parciais de cada etapa, serialização, limites, rotas, exportação, arquivos estáticos, métodos HTTP, cabeçalhos, controles da página e proteção contra acesso fora de `web/`. Também verificam que erros léxicos não sejam ignorados. Os testes anteriores do protótipo permanecem na suíte.

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
src/analise_lexica/modelo.py     TokenInfo e representação de um token
src/analise_lexica/erros.py      ErroLexico com linha e coluna
src/analise_lexica/analisador.py lexer ANTLR, iteração e análise completa
src/analise_lexica/cli.py        CLI de listagem de tokens
src/lexico.py                    fachada compatível e entrada da CLI E2
src/sintatico.py                 análise sintática e CLI
src/ast_morselang.py             nós da AST e representação em JSON
src/construir_ast.py             visitante que constrói a AST
src/analise_semantica/modelo.py  ResultadoSemantico, padrões e limites
src/analise_semantica/erros.py   ErroSemantico com linha e coluna
src/analise_semantica/analisador.py regras semânticas sobre a AST
src/analise_semantica/cli.py     CLI das etapas léxica, sintática e semântica
src/semantico.py                 fachada pública e entrada da CLI E4
src/execucao/modelo.py           Evento, Timeline e formatação dos tempos
src/execucao/erros.py            ErroExecucao
src/execucao/expansor.py         expansão das emissões em tons e silêncios
src/execucao/__main__.py         CLI da timeline de execução
src/geracao/texto.py             geração do arquivo .morse
src/geracao/audio.py             geração do arquivo .wav a partir da timeline
src/geracao/erros.py             ErroGeracao
src/geracao/__main__.py          CLI de exportação
src/visual/api.py                API JSON com tokens, AST, símbolos e timeline
src/visual/servidor.py           servidor HTTP local e arquivos estáticos
src/visual/__main__.py           CLI do servidor de visualização
src/visual/web/                  página, estilos e reprodução com Web Audio
tests/test_lexico.py             testes de tokens, erros, posições e CLI léxica
tests/test_sintatico.py          testes do parser, árvores e CLI
tests/test_semantico.py          testes das regras semânticas e CLI
tests/test_execucao.py           testes da timeline, durações e CLI
tests/test_geracao.py            testes do .morse, do .wav e da CLI
tests/test_visual.py             testes da API, exportação e servidor HTTP
exemplos/                       cinco programas sintática e semanticamente válidos
exemplos/invalidos/              três programas com erro léxico
exemplos/invalidos/sintaticos/    seis programas com erro sintático
exemplos/invalidos/semanticos/    seis programas com erro semântico
DIARIO.md                       registro das sessões de trabalho
```

`gerado/` é produzido pelo ANTLR e ignorado pelo Git.
