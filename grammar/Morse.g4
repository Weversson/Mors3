grammar Morse;

doc  : (word | WS)* EOF ;
word : SYMBOL+ ;

COMMENT : '//' ~[\r\n]* -> skip ;
WS      : [ \t\r\n]+ ;
SYMBOL  : ~[ \t\r\n] ;