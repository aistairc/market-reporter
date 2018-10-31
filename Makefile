OURS_CONF := config.toml
BASE_CONF := murakami-et-al-2017.toml
OURS_OPTS := --config $(OURS_CONF) --output-subdir ours
BASE_OPTS := --config $(BASE_CONF) --output-subdir base

OURS_SRC := output/ours/reporter.csv
OURS_TRG := output/ours.csv
BASE_SRC := output/base/reporter.csv
BASE_TRG := output/base.csv

.PHONY: all
all: ours base $(OURS_TRG) $(BASE_TRG)

ours: $(OURS_CONF)
	python -m reporter $(OURS_OPTS)
base: $(BASE_CONF)
	python -m reporter $(BASE_OPTS)

$(OURS_TRG): $(OURS_SRC)
	cp $(OURS_SRC) $(OURS_TRG)

$(BASE_TRG): $(BASE_SRC)
	cp $(BASE_SRC) $(BASE_TRG)

clean:
	rm -r output/ours* output/base*
