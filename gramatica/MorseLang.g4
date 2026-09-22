lexer grammar MorseLang;

MENSAGEM   : 'mensagem';
TOM        : 'tom';
VELOCIDADE : 'velocidade';
EMITIR     : 'emitir';

IGUAL      : '=';
MAIS       : '+';
VEZES      : '*';
ABRE_PAR   : '(';
FECHA_PAR  : ')';
PONTO_VIRGULA : ';';

REAL       : [0-9]+ '.' [0-9]+;
INTEIRO    : [0-9]+;
TEXTO      : '"' ~["\\\r\n]* '"';
IDENT      : [a-zA-Z_][a-zA-Z_0-9]*;

COMENTARIO : '//' ~[\r\n]* -> skip;
ESPACO     : [ \t\r\n]+ -> skip;
