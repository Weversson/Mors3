CC      ?= cc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra -Iinclude -MMD
LDLIBS   = -lm

SRC := $(wildcard src/*.c)
OBJ := $(SRC:.c=.o)

TARGET := mfcc

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $(OBJ) $(LDLIBS)

src/%.o: src/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(TARGET) $(OBJ) $(OBJ:.o=.d)

.PHONY: all clean