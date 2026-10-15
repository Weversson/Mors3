# Testes de entradas do parser MorseLang

Esta suíte testa exclusivamente a sintaxe de MorseLang e a construção da AST. Cada entrada é um arquivo independente. Os programas são lidos do disco e analisados pela implementação real em `src/sintatico.py`, com a gramática ANTLR oficial.

```text
testes_parser/
├── entradas_validas/      arquivos .mf que o parser deve aceitar
├── entradas_invalidas/    arquivos .mf que devem provocar ErroSintatico
├── orquestrador.sh        descoberta e execução de cada caso
├── verificar.py          verificação genérica e registro dos resultados
└── README.md
```

## Execução

Na raiz do projeto:

```sh
./testes_parser/orquestrador.sh
```

O script também pode ser chamado pelo caminho completo a partir de outra pasta. Ele prepara o ANTLR por meio de `make gen`, descobre recursivamente os arquivos `.mf`, executa cada caso e retorna 0 somente quando todos os casos descobertos passam. A primeira preparação pode precisar de internet para obter as dependências.

```sh
# Mostrar o resultado individual de todos os arquivos.
./testes_parser/orquestrador.sh --detalhado

# Selecionar uma família, mantendo o padrão entre aspas.
./testes_parser/orquestrador.sh --filtro '*precedencia*'

# Escolher a pasta para guardar relatórios e o limite por caso.
./testes_parser/orquestrador.sh --relatorios /tmp/meus-testes --timeout 5

# Usar outro conjunto de arquivos, com qualquer quantidade de entradas.
./testes_parser/orquestrador.sh --validas /caminho/validas --invalidas /caminho/invalidas
```

`PYTHON_PARSER` permite escolher o executável Python e `PARSER_TIMEOUT` define o limite por caso. O runtime ANTLR precisa estar disponível nesse Python. As opções e os caminhos são parâmetros de execução; não é necessário editar o orquestrador.

## Descoberta e resultado esperado

O shell não contém programas MorseLang, uma lista fixa de nomes nem uma quantidade esperada de testes. Todo `.mf` encontrado entra na execução. Para incluir um caso, basta criar um arquivo na pasta correspondente. O nome do arquivo não determina a aceitação: quem determina o resultado esperado é a pasta.

Todos os arquivos precisam ser lexicamente válidos. O verificador confere essa pré-condição antes de chamar o parser. Um arquivo em `entradas_invalidas` só passa quando provoca **ErroSintatico**. Erro léxico, falha de leitura, JSON incorreto, exceção interna ou estouro de tempo contam como falha da suíte, nunca como uma rejeição sintática correta.

Cada execução usa uma pasta nova de relatórios, informa seu caminho e preserva:

- `resultados.jsonl`: entrada realmente lida, SHA-256, classificação esperada, resultado observado, AST/árvore ou erro, duração e motivo de eventual falha;
- `resumo.json`: quantidade descoberta e registrada, aprovados, falhas, contagem por classe, comparações adicionais e arquivos com falha.

Esses relatórios ficam em uma pasta temporária por padrão. As pastas de execução
`morselang-parser.*`, os arquivos `resultados.jsonl` e `resumo.json` e os logs
`*.log` são ignorados pelo Git, inclusive quando `--relatorios` aponta para dentro
do projeto. Somente as entradas `.mf`, suas expectativas `.json` e o código da
suíte devem ser versionados; saídas de execução permanecem locais.

As contagens são calculadas dos arquivos encontrados e dos resultados observados. Nenhum resultado é pré-preenchido. Uma seleção sem arquivos retorna erro; uma execução sem registros não é aprovada.

## Cobertura do conjunto de entradas

O conjunto foi construído a partir das regras da especificação, sem usar a resposta do parser para decidir a pasta de cada entrada. Os limites abaixo tornam a exploração finita; não significam que todas as entradas possíveis da linguagem tenham sido testadas.

| Família | Variações cobertas |
|---------|-------------------|
| Ordem dos comandos | Todas as sequências de zero a cinco comandos dos tipos mensagem, tom, velocidade e emissão |
| Preâmbulos longos | Declarações e configurações em todas as posições permitidas para preâmbulos de seis a oito comandos, seguidos de uma a três emissões |
| Átomos | Texto vazio, Unicode, símbolos dentro de textos e diferentes identificadores |
| Concatenação e repetição | Pares de operandos, encadeamentos, combinações de operadores e números com zeros à esquerda |
| Precedência e associatividade | Repetição à esquerda e à direita da concatenação, agrupamento explícito e cadeias associadas à esquerda |
| Parênteses | Aninhamentos até 64 níveis, grupos vazios, fechamento ausente ou excedente e números em posição de expressão |
| Configurações | Tom inteiro/real, velocidade inteira, configurações duplicadas, operandos e pontuação incorretos |
| Separadores | Espaços, tabulações, LF, CRLF, CR, comentários entre tokens e entrada sem quebra final |
| Volume | Até 256 declarações ou emissões, identificadores longos e números com milhares de dígitos |
| Estruturas incompletas | Ausência de nome, valor, operador, ponto e vírgula, emissão ou parte da expressão |
| Consumo da fonte | Texto excedente e erros depois de um prefixo longo de emissões válidas |
| Diagnósticos | Comparação de posições de erros com expectativas externas |
| Fronteira semântica | Nomes não resolvidos, redefinições e valores zero continuam sintaticamente aceitos |

Entradas exatamente repetidas foram eliminadas na construção do conjunto. Os nomes dos arquivos indicam a família e a combinação exercitada. A maior parte dos arquivos inclui um comentário de identificação; casos de arquivo vazio, separadores e posições preservam sua forma específica.

## Expectativas adicionais em JSON

O arquivo `caso.mf` pode ter um `caso.json` ao lado. Esse JSON é opcional para novos casos. As expectativas existentes foram construídas a partir do agrupamento pretendido, sem copiar as árvores produzidas pelo parser.

Para comparar a AST completa de `emitir "SOS";`, o formato é:

```json
{
  "ast": {
    "tipo": "Programa",
    "comandos": [
      {"tipo": "Emissao", "expressao": {"tipo": "Texto", "valor": "SOS"}}
    ]
  }
}
```

Linhas e colunas são removidas apenas na comparação estrutural da AST. Por isso, uma mudança de espaços ou comentários não altera o agrupamento esperado. Precedência e associatividade incorretas fazem o teste falhar mesmo que o parser aceite o programa.

Para exigir uma posição de erro, use, por exemplo:

```json
{"erro": {"linha": 1, "coluna": 8}}
```

Um JSON de AST só é permitido junto de uma entrada válida; uma expectativa de erro só é permitida junto de uma entrada inválida. Alterar a entrada sem atualizar uma expectativa correspondente pode fazer o teste falhar, como deve ocorrer.

## Limites da etapa

Esta suíte não executa mensagens nem testa geração de Morse ou WAV. A aceitação de um nome não declarado ou de uma repetição por zero demonstra somente validade sintática. Resolução de nomes, limites numéricos e demais verificações semânticas pertencem à E4.

Os testes anteriores em `tests/` continuam disponíveis por `make test`. O corpus de arquivos desta pasta é executado pelo seu próprio orquestrador shell.
