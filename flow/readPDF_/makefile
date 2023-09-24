# introduced in make3.81
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
ROOT_DIR := $(strip $(ROOT_DIR))

export GOOGLE_APPLICATION_CREDENTIALS = $(ROOT_DIR)/../../.secrets/google.token
export PYTHONPATH := $(ROOT_DIR)/../src:$(PYTHONPATH)

.PHONY: all

all: 
	poetry run python src/readPDF.py input output > logs/info.log

%:
	poetry run python src/readPDF.py input/mahmls-$@.pdf output/mahmls-$@.pdf.doc.json
