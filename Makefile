PYTHON_BIN	?= python3
VENV		:= .venv
PYTHON		:= $(VENV)/bin/python
MAPS_DIR	:= maps
LEVEL		?= easy
NUM			?= 1
MAP			?= $(firstword $(wildcard \
			   $(MAPS_DIR)/$(LEVEL)/$(shell printf '%02d' $(NUM))_*.txt))
ARGS		?=

MYPY_FLAGS	:= --warn-return-any --warn-unused-ignores \
			   --ignore-missing-imports --disallow-untyped-defs \
			   --check-untyped-defs

.PHONY: all install run gui debug maps check-map clean fclean lint lint-strict

all: run

$(PYTHON):
	$(PYTHON_BIN) -m venv $(VENV)

install: $(PYTHON)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run: check-map
	$(PYTHON) fly_in.py $(MAP) $(ARGS)

gui: check-map
	$(PYTHON) fly_in.py $(MAP) --gui $(ARGS)

debug: check-map
	$(PYTHON) -m pdb fly_in.py $(MAP) $(ARGS)

maps:
	@for dir in $(MAPS_DIR)/*/; do \
		level=$$(basename $$dir); \
		for f in $$dir*.txt; do \
			name=$$(basename $$f .txt); \
			num=$$(echo $$name | cut -d_ -f1 | sed 's/^0*//'); \
			echo "make run LEVEL=$$level NUM=$$num    # $$f"; \
		done; \
	done

check-map:
	@if [ -z "$(MAP)" ] || [ ! -f "$(MAP)" ]; then \
		echo "Error: no map for LEVEL=$(LEVEL) NUM=$(NUM)" \
			"(see 'make maps')" >&2; \
		exit 1; \
	fi

clean:
	find . -path ./$(VENV) -prune -o -type d -name __pycache__ \
		-exec rm -rf {} +
	rm -rf .mypy_cache

fclean: clean
	rm -rf $(VENV)

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . $(MYPY_FLAGS)

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict
