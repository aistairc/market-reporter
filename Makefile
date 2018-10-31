REPORTER := python -m reporter
CP := cp
OURS := ours
BASE := base
OURSCONF := config.toml
BASECONF := murakami-et-al-2017.toml
OURSOPTS := --config $(OURSCONF) --output-subdir $(OURS)
BASEOPTS := --config $(BASECONF) --output-subdir $(BASE)

OUTPUTDIR := output
OURSSRC := $(OUTPUTDIR)/$(OURS)/reporter.csv
OURSTRG := $(OUTPUTDIR)/$(OURS).csv
BASESRC := $(OUTPUTDIR)/$(BASE)/reporter.csv
BASETRG := $(OUTPUTDIR)/$(BASE).csv
CPOURS := $(CP) $(OURSSRC) $(OURSTRG)
CPBASE := $(CP) $(BASESRC) $(BASETRG)

.PHONY: all
all: $(OURS) $(BASE) $(OURSTRG) $(BASETRG)

${OURS}: $(OURSCONF)
	$(REPORTER) $(OURSOPTS)
${BASE}: $(BASECONF)
	$(REPORTER) $(BASEOPTS)

$(OURSTRG): $(OURSSRC)
	$(CPOURS)

$(BASETRG): $(BASESRC)
	$(CPBASE)

clean:
	rm -r $(OUTPUTDIR)/$(OURS) $(OUTPUTDIR)/$(BASE) $(OURSTRG) $(BASETRG)
