ours_conf = config.toml
base_conf = murakami-et-al-2017.toml

ours_src = output/ours/reporter.csv
ours_trg = output/ours.csv
base_src = output/base/reporter.csv
base_trg = output/base.csv

.PHONY: all
all: ours base $(ours_trg) $(base_trg)

ours: $(ours_conf)
	python -m reporter --config $(ours_conf) --output-subdir ours
base: $(base_conf)
	python -m reporter --config $(base_conf) --output-subdir base

$(ours_trg): $(ours_src)
	cp $(ours_src) $(ours_trg)

$(base_trg): $(base_src)
	cp $(base_src) $(base_trg)

clean:
	rm -r output/ours* output/base*
