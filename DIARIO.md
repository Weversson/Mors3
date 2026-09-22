# Diário de desenvolvimento

## 22/09/2026

Comparamos o protótipo de tradução de texto para Morse com o enunciado da E2. A regra `SYMBOL` aceitava quase todos os caracteres isoladamente; por isso, o projeto não distinguia identificadores, números, texto literal, palavras-chave e operadores, nem apontava erros léxicos com linha e coluna.

Definimos MorseLang como uma linguagem pequena de composição de mensagens. Criamos uma gramática ANTLR só de lexer, três exemplos válidos, três inválidos e `src/lexico.py` para listar os tokens. A primeira execução direta do programa falhou porque `src/ast.py` ocultava o módulo `ast` da biblioteca padrão; ajustamos o caminho de importação e repetimos os exemplos com sucesso.

Geramos temporariamente um parser ANTLR com `tokenVocab=MorseLang` e analisamos os três exemplos válidos sem erro sintático. Esse experimento mostra que os tokens da E2 podem ser usados na E3. A verificação final passou em 61 testes; `make run` listou os tokens do exemplo e `make prototype` ainda gerou os arquivos do tradutor antigo.
