parser grammar MorseLangParser;

options { tokenVocab=MorseLang; }

programa : preambulo emissao+ EOF ;

// Mensagens podem aparecer antes, entre e depois das configurações.
// Cada configuração é opcional, ocorre no máximo uma vez e aceita ambas
// as ordens. Depois da primeira emissão, só pode haver outras emissões.
preambulo
    : declaracao*
      ( configuracaoTom declaracao* (configuracaoVelocidade declaracao*)?
      | configuracaoVelocidade declaracao* (configuracaoTom declaracao*)?
      )?
    ;

declaracao            : MENSAGEM IDENT IGUAL expressao PONTO_VIRGULA ;
configuracaoTom       : TOM (REAL | INTEIRO) PONTO_VIRGULA ;
configuracaoVelocidade: VELOCIDADE INTEIRO PONTO_VIRGULA ;
emissao              : EMITIR expressao PONTO_VIRGULA ;

// A separação em níveis dá maior precedência à repetição.
// O visitante agrupa as cadeias de operadores da esquerda para a direita.
expressao : termo (MAIS termo)* ;
termo     : atomo (VEZES INTEIRO)* ;
atomo     : TEXTO | IDENT | ABRE_PAR expressao FECHA_PAR ;
