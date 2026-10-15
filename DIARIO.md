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
