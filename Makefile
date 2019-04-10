output_dir := output

ours_conf := config.toml
ours := $(output_dir)/ours.csv

base_conf := murakami-et-al-2017.toml
base := $(output_dir)/base.csv

.PHONY: all clean
all: $(ours) $(base)

$(ours): $(ours_conf)
	@python -m reporter --config $(ours_conf) --output-subdir ours
	@mv $(output_dir)/ours/reporter.csv  $(ours)

$(base): $(base_conf)
	@python -m reporter --config $(base_conf) --output-subdir base
	@mv $(output_dir)/base/reporter.csv  $(base)

clean:
	@rm -r output/ours* output/base*
