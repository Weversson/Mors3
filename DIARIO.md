# Diário de desenvolvimento

Este diário registra as etapas de 09 e 22 de setembro e de 14 de outubro de 2026. O relato de 09/09 foi organizado a partir dos arquivos do protótipo preservados no projeto.

## 09/09/2026: primeira proposta e protótipo

Começamos com a ideia de ler um arquivo `.mf` contendo texto livre e transformá-lo em duas saídas: uma representação textual em código Morse, salva como `.morse`, e um arquivo de áudio `.wav`. Nesse momento, `.mf` era apenas a extensão do arquivo de entrada. Ainda não havia uma linguagem com comandos, variáveis ou expressões.

Construímos um primeiro protótipo em C, preservado em `legacy_c/`, com leitura do arquivo, separação de símbolos e palavras, tabela Morse e geração das saídas. Também organizamos uma versão em Python com ANTLR. Nela, `grammar/Morse.g4` reconhecia palavras formadas por símbolos, espaços e comentários. O programa `mfcc.py` recebia o arquivo de entrada e permitia ajustar a frequência do tom e a velocidade do áudio por argumentos da linha de comando.

As dificuldades dessa etapa estavam ligadas à conversão do texto. Era necessário separar palavras sem perder os intervalos corretos no áudio, distinguir ponto e traço pela duração e decidir o que fazer com caracteres que não tinham correspondência na tabela Morse. O protótipo passou a normalizar letras acentuadas e a avisar quando ignorava caracteres sem código. Os testes preservados verificam a tabela, a estrutura do texto Morse, a duração dos sinais, os espaços de silêncio e a geração do arquivo WAV.

Ao final dessa etapa, o tradutor de texto livre funcionava como protótipo. Sua gramática, porém, aceitava quase qualquer caractere não branco como `SYMBOL`. Isso era suficiente para a conversão inicial, mas não definia os elementos de uma linguagem de programação.

## 22/09/2026: adequação à atividade E2

Ao comparar o protótipo com o enunciado da E2, percebemos que a atividade exigia uma linguagem pequena e um analisador léxico capaz de reconhecer categorias distintas. O tradutor anterior não separava palavras-chave, identificadores, números, textos literais e operadores. Também não apresentava erros léxicos com linha e coluna. Por isso, mantivemos a conversão de texto como protótipo e definimos MorseLang como a linguagem do projeto.

Registramos em `docs/especificacao.md` o propósito da linguagem, um programa de exemplo, seus tipos, comandos, operadores, comentários e limites deliberados. A proposta inclui os comandos `mensagem`, `tom`, `velocidade` e `emitir`, além de concatenação e repetição de texto. O objetivo é aproveitar o domínio de código Morse sem antecipar a implementação completa do interpretador.

Para a E2, criamos `gramatica/MorseLang.g4` como uma gramática ANTLR apenas de lexer e `src/lexico.py` para listar cada token com seu tipo, texto, linha e coluna. Acrescentamos três programas léxicos válidos e três com erros, além de um script para gerar o lexer. Durante a primeira execução direta, `src/ast.py` ocultou o módulo `ast` da biblioteca padrão do Python; corrigimos o caminho de importação e repetimos a validação.

Os testes passaram em 61 casos, incluindo os exemplos válidos e inválidos, as posições dos tokens e os testes do protótipo anterior. Também geramos temporariamente um parser ANTLR que reutilizou os tokens de MorseLang e aceitou os três exemplos válidos. Esse teste indica que o lexer pode servir de base para a E3, sem afirmar que a análise sintática já esteja implementada no projeto.

A entrega atual reconhece tokens, mas ainda não executa programas MorseLang. A análise sintática fica para a E3; a análise semântica e a geração de `.morse` e `.wav` a partir da nova linguagem ficam para a E4.

## 14/10/2026: implementação do analisador sintático E3

Implementamos a gramática permanente `gramatica/MorseLangParser.g4`, reutilizando os tokens do lexer da E2. A regra inicial exige pelo menos um comando `emitir` e consome o arquivo inteiro até `EOF`. O preâmbulo permite declarações de mensagem intercaladas com as configurações, restringindo `tom` e `velocidade` a uma ocorrência cada e impedindo novos comandos de configuração ou declaração após a primeira emissão.

Separamos as expressões em expressão, termo e átomo para representar a precedência da repetição sobre a concatenação e o efeito dos parênteses. Criamos `src/ast_morselang.py` e um visitante para construir a AST com comandos, referências, literais, concatenações e repetições. O visitante associa os operadores à esquerda e mantém a posição inicial dos nós na fonte. Essa AST é independente da estrutura de palavras e símbolos do protótipo anterior.

Acrescentamos a CLI `src/sintatico.py`, com validação simples, árvore concreta por `--arvore` e AST em JSON por `--ast`. Compartilhamos a criação do lexer com a E2 para impedir que caracteres inválidos sejam descartados silenciosamente antes do parsing. Os erros léxicos e sintáticos interrompem a análise, retornam código 1 e apresentam linha e coluna. O script `gerar.sh` passou a gerar também o parser e o visitante, e `make sintatico` executa a nova etapa.

Substituímos o teste temporário de viabilidade pelos testes do parser permanente. Acrescentamos dois exemplos válidos e seis exemplos de erros sintáticos. A execução de `make test` passou nos 90 testes, incluindo os testes anteriores, precedência, associatividade, ordens possíveis do preâmbulo, rejeição de estruturas inválidas, posições dos erros, saída JSON e execução fora do diretório do projeto. Os testes também confirmam que esta etapa não produz arquivos de áudio.

A análise semântica e a execução continuam pendentes para a E4. O parser não resolve nomes, não verifica positividade ou limites dos valores, não aplica os parâmetros padrão e não converte mensagens em Morse. A especificação e o README foram atualizados para deixar essa fronteira explícita.

## 04/11/2026: modularização e validação do analisador léxico

Reorganizamos a implementação da E2, que até então concentrava modelo de token, erro, lexer e CLI em `src/lexico.py`. O pacote `src/analise_lexica` passou a separar essas responsabilidades: `modelo.py` define `TokenInfo`, `erros.py` define `ErroLexico`, `analisador.py` cria o lexer ANTLR e expõe `iterar_tokens` e `analisar`, e `cli.py` mantém a listagem de tokens. `src/lexico.py` continuou como fachada compatível e entrada da CLI, e o parser passou a importar a API canônica do pacote.

A gramática ANTLR permaneceu como fonte de verdade dos tokens. As mensagens de erro léxico foram traduzidas para deixar explícito o trecho não reconhecido, preservando linha e coluna contadas a partir de 1. A suíte `tests/test_lexico.py` foi ampliada para cobrir palavras-chave, identificadores, números, textos, pontuação, comentários, espaços, LF/CRLF, Unicode, primeiro erro, exemplos válidos e inválidos, execução direta, execução como módulo e a CLI com saídas injetadas.

A validação final passou nos 114 testes da suíte. Também executamos a análise léxica sobre os 4413 arquivos `.mf` de `testes_parser`, somando 71323 tokens sem nenhum erro léxico. Isso confirma a pré-condição já documentada para o parser: todas aquelas entradas são lexicamente válidas. A análise sintática e a construção da AST não foram alteradas, e a análise semântica e a execução continuam na E4.

## 04/11/2026: implementação da análise semântica E4

Implementamos a análise semântica como um estágio separado sobre a AST produzida pela E3. O novo pacote `src/analise_semantica` segue a organização modular do lexer: `modelo.py` define `ResultadoSemantico`, os padrões e os limites; `erros.py` define `ErroSemantico`; `analisador.py` percorre comandos e expressões; e `cli.py` encadeia as análises léxica, sintática e semântica. `src/semantico.py` funciona como fachada pública e entrada da CLI, também disponível por `python -m src.analise_semantica`. O alvo `make semantico` foi acrescentado ao Makefile.

As regras implementadas exigem nomes declarados antes do uso e sem redefinição, repetição com inteiro positivo, tom entre 100 e 20000 Hz, velocidade com inteiro positivo e caracteres com representação na tabela Morse fixa. Todos os literais são validados, inclusive em mensagens nunca emitidas. Acentos são normalizados, espaços separam palavras e texto vazio é aceito. O resultado aplica os padrões de 600 Hz e 20 palavras por minuto e preserva `tom` e `velocidade` como `Decimal`, sem converter os lexemas antes das verificações. A análise para no primeiro erro e não expande repetições nem gera `.morse` ou `.wav`.

Acrescentamos `tests/test_semantico.py` com 56 casos, cobrindo os padrões, a resolução e a redefinição de nomes, repetições com zeros à esquerda, os limites inclusivos do tom, velocidade positiva, acentos e símbolos sem Morse, posições dos diagnósticos, primeiro erro, reutilização do analisador, execução da CLI direta e modular, saídas injetadas e ausência de arquivos gerados. Também criamos `exemplos/invalidos/semanticos/` com seis programas que passam pelo lexer e pelo parser, mas falham na análise semântica.

A suíte completa passou nos 170 testes. A execução dos comandos `emitir` e a geração das saídas continuam pendentes; nesta etapa o programa é apenas validado e as configurações efetivas são calculadas.

## 04/11/2026: execução headless e timeline de eventos

Implementamos a primeira parte da execução em `src/execucao`, separando modelo, diagnóstico e expansão. `Evento` representa um tom ou silêncio com início, duração, motivo, emissão, caractere e símbolo; `Timeline` reúne tom, velocidade, unidade, textos expandidos e a sequência de eventos. A API `expandir(resultado)` recebe o `ResultadoSemantico`, resolve referências, concatenações e repetições e aplica o padrão PARIS: ponto de `1200 / WPM` milissegundos, traço de três pontos, silêncio de um ponto entre símbolos, três entre caracteres e sete entre palavras e emissões. `expandir_texto` permite expandir uma expressão isolada.

Emissões distintas são unidas por um espaço e espaços em branco são normalizados como separadores de palavra. Texto vazio não gera eventos. A expansão aceita um limite opcional de caracteres para proteger interfaces interativas, sem alterar o comportamento padrão da linguagem. A CLI `python -m src.execucao` imprime a timeline em JSON; `--resumo` mostra apenas as contagens e `--limite` aplica a proteção. O alvo `make timeline` foi acrescentado ao Makefile. Nenhum arquivo `.morse` ou `.wav` é gerado e nenhum áudio é reproduzido.

Acrescentamos `tests/test_execucao.py` com 49 casos, cobrindo a unidade PARIS, concatenação, repetição, referências, normalização de espaços, separação entre emissões, durações, contiguidade dos eventos, limites, modelo, JSON, exemplos e a CLI. A suíte completa passou nos 219 testes. A próxima etapa é a interface web local com Web Audio para visualizar e ouvir a timeline em tempo real.

## 04/11/2026: visualização web local e reprodução com Web Audio

Implementamos a interface de visualização em `src/visual`, mantendo o servidor restrito à biblioteca padrão. `api.py` executa léxica, sintática, semântica e execução e devolve um dicionário JSON com tokens, AST, símbolos, tom, velocidade e timeline. Erros de análise não viram falhas HTTP: a resposta mantém status 200, `ok: false`, a etapa, linha, coluna e detalhe, além dos tokens e da AST disponíveis até a falha. `servidor.py` usa `ThreadingHTTPServer`, serve os arquivos de `web/` com proteção contra acesso fora do diretório, aplica limite de 1 MB ao corpo e responde 4xx para requisições malformadas, métodos incorretos e caminhos inexistentes. `__main__.py` oferece `--host`, `--porta`, `--limite`, `--abrir` e `--verboso`, e o alvo `make visual` inicia o servidor.

A página em `src/visual/web/` analisa a fonte a cada edição, com debounce e descarte de respostas antigas. Ela mostra métricas, tokens, símbolos, AST e uma faixa proporcional de tons e silêncios. A reprodução cria um `AudioContext`, agenda um único oscilador para toda a timeline e automatiza o ganho para soar apenas nos eventos de tom na frequência efetiva; o cursor e o destaque do evento acompanham o relógio do áudio por `requestAnimationFrame`. Há controles de reproduzir, pausar, continuar, reiniciar e volume, e uma nova análise interrompe a reprodução anterior. A faixa representa até 800 eventos, mas o áudio cobre a timeline completa.

Acrescentamos `tests/test_visual.py` com 36 casos, cobrindo o contrato da API, erros parciais de cada etapa, serialização, limites, rotas, arquivos estáticos, métodos HTTP, cabeçalhos, proteção do diretório web, controles da página e uso de Web Audio. A suíte completa passou nos 255 testes. README, especificação e este diário foram atualizados.

## 18/11/2026: geração de arquivos `.morse` e `.wav`

Fechamos o fluxo da linguagem com o pacote `src/geracao`, separado de `src/execucao`. A timeline continua sendo a única fonte de tempos, símbolos e frequência: `texto.py` serializa um texto Morse com uma linha por emissão, caracteres separados por espaço e palavras por ` / `; `audio.py` converte os eventos de tom em PCM de 16 bits e grava um WAV mono com a biblioteca padrão, usando uma curta rampa para evitar estalos. A CLI `python -m src.geracao` grava os dois arquivos ao lado da entrada por padrão e aceita `--morse`, `--wav`, `--taxa` e `--limite`. O alvo `make exportar` foi acrescentado ao Makefile.

Reutilizamos o pipeline da visualização para a exportação. `src/visual/api.py` passou a expor `analisar_timeline`, e o servidor ganhou `POST /api/exportar`, que recebe `fonte` e `formato` e devolve o arquivo com `Content-Disposition: attachment`. A página ganhou os botões **Baixar .morse** e **Baixar .wav**. Erros de análise continuam sendo JSON com `ok: false`, enquanto requisições inválidas retornam 4xx.

Acrescentamos `tests/test_geracao.py` com 21 casos, cobrindo o formato textual, acentos, emissões vazias, cabeçalho e samples do WAV, frequência do tom, silêncios, limites de amplitude, opções inválidas e a CLI. Estendemos `tests/test_visual.py` com 8 casos de exportação. A suíte completa passou nos 284 testes. README e especificação foram atualizados; o fluxo de ponta a ponta agora analisa, visualiza, reproduz e grava as saídas.
