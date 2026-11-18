# Testes semânticos de MorseLang

Esta suíte executa a cadeia completa **léxica -> sintática -> semântica** sobre
um corpus externo de programas `.mf`. Ela complementa os testes unitários de
`tests/test_semantico.py`: os arquivos e as expectativas ficam separados do
código do analisador.

```text
testes_semanticos/
├── entradas_validas/      programas que devem passar pelas três etapas
├── entradas_invalidas/    programas que devem falhar na etapa semântica
├── orquestrador.sh        descoberta e execução de cada caso
├── verificar.py           verificação genérica e gravação dos resultados
└── README.md
```

## Execução

Na raiz do projeto:

```sh
make test-semantico
./testes_semanticos/orquestrador.sh
```

A suíte também pode ser chamada a partir de outra pasta:

```sh
./testes_semanticos/orquestrador.sh --detalhado
./testes_semanticos/orquestrador.sh --filtro '*tom*'
./testes_semanticos/orquestrador.sh --relatorios /tmp/meus-testes --timeout 5
./testes_semanticos/orquestrador.sh --validas /caminho/validas \
    --invalidas /caminho/invalidas
```

`PYTHON_SEMANTICO` escolhe o executável Python e `SEMANTICO_TIMEOUT` define o
limite por caso. Se `gerado/MorseLangParser.py` ainda não existir, o
orquestrador chama `make gen` uma única vez; depois disso, a execução usa o
parser já gerado.

## Descoberta e classificação

Todo `.mf` encontrado nas duas pastas entra na execução, inclusive em subpastas.
A pasta determina a classificação esperada:

- `entradas_validas`: o programa deve ser aceito por `analisar_fonte`.
- `entradas_invalidas`: o programa deve produzir `ErroSemantico`.

Entradas do corpus semântico precisam ser lexicamente e sintaticamente válidas.
Um erro léxico ou sintático é registrado como falha de escopo, nunca como uma
rejeição semântica correta. O verificador também confere que entradas inválidas
não foram aceitas e que entradas válidas não foram rejeitadas.

## Expectativas opcionais em JSON

O arquivo `caso.mf` pode ter um `caso.json` ao lado. Para entradas válidas, o
JSON pode fixar as configurações efetivas e as contagens:

```json
{
  "tom": "600",
  "velocidade": "20",
  "emissoes": 1,
  "mensagens": 0
}
```

Os valores de `tom` e `velocidade` são comparados como `Decimal`, preservando a
igualdade numérica entre `600` e `600.0`. Para entradas inválidas, o JSON pode
fixar a posição e um trecho do diagnóstico:

```json
{
  "erro": {
    "linha": 1,
    "coluna": 8,
    "detalhe_contem": "não foi declarado"
  }
}
```

Também é possível usar `detalhe` para exigir a mensagem completa. Uma
expectativa de configuração só é permitida em entrada válida; uma expectativa
de erro só é permitida em entrada inválida.

## Relatórios e integração

Cada execução cria uma pasta temporária `morselang-semantico.*` e grava:

- `resultados.jsonl`: arquivo, hash, classe, expectativa, resultado observado,
  duração e motivo de eventual falha;
- `resumo.json`: quantidades descobertas/registradas, aprovados, falhas,
  contagem por classe, comparações de configuração/erro e arquivos com falha.

`make test` executa os testes unitários e esta suíte semântica. Para rodar
somente as etapas separadas:

```sh
make test-unitario    # unittest discover em tests/
make test-semantico   # corpus deste diretório
```
