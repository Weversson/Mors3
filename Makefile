ANTLR_VERSION := 4.13.2
ANTLR_JAR := tools/antlr-$(ANTLR_VERSION)-complete.jar
ANTLR_URL := https://www.antlr.org/download/antlr-$(ANTLR_VERSION)-complete.jar
PY := .venv/bin/python
RUNTIME_STAMP := .venv/.antlr-runtime-$(ANTLR_VERSION)
INPUT ?= exemplos/ola.mf

.PHONY: all setup gen gen-prototipo run prototype test clean

all: gen

setup: $(ANTLR_JAR) $(RUNTIME_STAMP)

$(RUNTIME_STAMP):
	python3 -m venv .venv
	$(PY) -m pip install -q antlr4-python3-runtime==$(ANTLR_VERSION)
	touch $@

$(ANTLR_JAR):
	mkdir -p tools
	curl -sSL -o $@ $(ANTLR_URL)

gen: setup
	ANTLR_VERSION=$(ANTLR_VERSION) ./gerar.sh

gen-prototipo: setup
	mkdir -p generated
	touch generated/__init__.py
	cd grammar && java -jar ../$(ANTLR_JAR) -Dlanguage=Python3 -o ../generated Morse.g4
	rm -f generated/*.interp generated/*.tokens

run: gen
	$(PY) src/lexico.py $(INPUT)

prototype: gen-prototipo
	$(PY) mfcc.py -o /tmp/mfcc_prototype examples/olamundo.mf

test: gen gen-prototipo
	$(PY) -m unittest discover -s tests -v

clean:
	rm -rf .venv generated gerado tools
	rm -rf src/__pycache__ tests/__pycache__
	rm -f examples/*.morse examples/*.wav
