#include "morse.h"

#include <ctype.h>
#include <stddef.h>

typedef struct {
    int code;
    const char *morse;
} MorseEntry;

static const MorseEntry table[] = {
    {'A', ".-"},     {'B', "-..."},   {'C', "-.-."},  {'D', "-.."},
    {'E', "."},      {'F', "..-."},   {'G', "--."},   {'H', "...."},
    {'I', ".."},     {'J', ".---"},   {'K', "-.-"},   {'L', ".-.."},
    {'M', "--"},     {'N', "-."},     {'O', "---"},   {'P', ".--."},
    {'Q', "--.-"},   {'R', ".-."},    {'S', "..."},   {'T', "-"},
    {'U', "..-"},    {'V', "...-"},   {'W', ".--"},   {'X', "-..-"},
    {'Y', "-.--"},   {'Z', "--.."},
    {'0', "-----"},  {'1', ".----"},  {'2', "..---"}, {'3', "...--"},
    {'4', "....-"},  {'5', "....."},  {'6', "-...."}, {'7', "--..."},
    {'8', "---.."},  {'9', "----."},
    {'.', ".-.-.-"}, {',', "--..--"}, {'?', "..--.."}, {'\'', ".----."},
    {'!', "-.-.--"}, {'/', "-..-."},  {'(', "-.--."},  {')', "-.--.-"},
    {'&', ".-..."},  {':', "---..."}, {';', "-.-.-."}, {'=', "-...-"},
    {'+', ".-.-."},  {'-', "-....-"}, {'_', "..--.-"}, {'"', ".-..-."},
    {'$', "...-..-"}, {'@', ".--.-."},
};

static const size_t table_len = sizeof table / sizeof table[0];

static int normalize(int c) {
    switch (c) {
        case 0x00c0: case 0x00c1: case 0x00c2: case 0x00c3:
        case 0x00c4: case 0x00c5:
        case 0x00e0: case 0x00e1: case 0x00e2: case 0x00e3:
        case 0x00e4: case 0x00e5:
            return 'A';
        case 0x00c7: case 0x00e7: return 'C';
        case 0x00c8: case 0x00c9: case 0x00ca: case 0x00cb:
        case 0x00e8: case 0x00e9: case 0x00ea: case 0x00eb:
            return 'E';
        case 0x00cc: case 0x00cd: case 0x00ce: case 0x00cf:
        case 0x00ec: case 0x00ed: case 0x00ee: case 0x00ef:
            return 'I';
        case 0x00d1: case 0x00f1: return 'N';
        case 0x00d2: case 0x00d3: case 0x00d4: case 0x00d5:
        case 0x00d6: case 0x00d8:
        case 0x00f2: case 0x00f3: case 0x00f4: case 0x00f5:
        case 0x00f6: case 0x00f8:
            return 'O';
        case 0x00d9: case 0x00da: case 0x00db: case 0x00dc:
        case 0x00f9: case 0x00fa: case 0x00fb: case 0x00fc:
            return 'U';
        case 0x00dd: case 0x0178:
        case 0x00fd: case 0x00ff:
            return 'Y';
        default:
            return toupper(c);
    }
}

const char *morse_for(int c) {
    int up = normalize(c);
    for (size_t i = 0; i < table_len; i++) {
        if (table[i].code == up) return table[i].morse;
    }
    return NULL;
}

int morse_supported(int c) {
    return morse_for(c) != NULL;
}