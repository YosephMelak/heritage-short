PYTHON ?= python

.PHONY: validate smoke narration radio-cut keyframes music shots assemble film clean

validate:
	$(PYTHON) -m pipeline.validate

smoke:
	$(PYTHON) -m pipeline.smoke_test

narration:
	$(PYTHON) -m pipeline.narration

radio-cut:
	$(PYTHON) -m pipeline.assemble --mode radio-cut

keyframes:
	$(PYTHON) -m pipeline.keyframes

music:
	$(PYTHON) -m pipeline.music

shots:
	$(PYTHON) -m pipeline.shots

assemble:
	$(PYTHON) -m pipeline.assemble --mode final

film:
	$(PYTHON) -m pipeline.run

clean:
	$(PYTHON) -c "import pathlib, shutil; p=pathlib.Path('outputs/temp'); shutil.rmtree(p, ignore_errors=True)"
