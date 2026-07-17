all: dos2unix black isort pylint i18n_check dlint_python dlint_r

black:
	@echo "Code formatting"
	poetry run black bin/*.py

isort:
	@echo "Imports sorting"
	poetry run isort bin/*.py

pylint:
	@echo "Code QC"
	poetry run pylint bin/*.py --no-docstring-rgx='^_|^main$$' --extension-pkg-whitelist=numpy

dos2unix:
	@echo "Reformatting"
	dos2unix bin/*.py

i18n_check:
	@echo "i18n catalog QC"
	poetry run python utils/check_i18n_catalog.py

dlint_python:
	@echo "Lint Python Dockerfile"
	cat images/Python/Dockerfile | docker run --rm -i hadolint/hadolint

dlint_r_sesame:
	@echo "Lint R SeSAME Dockerfile"
	cat images/R_sesame/Dockerfile | docker run --rm -i hadolint/hadolint

dlint_r_clock:
	@echo "Lint R clock Dockerfile"
	cat images/R_clock/Dockerfile | docker run --rm -i hadolint/hadolint

fetch_example_data:
	@echo "Downloading example IDAT data from GEO GSE86831..."
	bash examples/fetch_example_data.sh

run_example: fetch_example_data
	nextflow run main.nf -params-file examples/params.json

clean_example:
	rm -rf examples/idats examples/results/*
	@touch examples/results/.gitkeep
