all: dos2unix black isort pylint dlint_python dlint_r

black:
	@echo "Code formatting"
	poetry run black bin/*.py

isort:
	@echo "Imports sorting"
	poetry run isort bin/*.py

pylint:
	@echo "Code QC"
	poetry run pylint bin/*.py

dos2unix:
	@echo "Reformatting"
	dos2unix bin/*.py

dlint_python:
	@echo "Lint Python Dockerfile"
	cat images/Python/Dockerfile | docker run --rm -i hadolint/hadolint

dlint_r_sesame:
	@echo "Lint R SeSAME Dockerfile"
	cat images/R_sesame/Dockerfile | docker run --rm -i hadolint/hadolint

dlint_r_clock:
	@echo "Lint R clock Dockerfile"
	cat images/R_clock/Dockerfile | docker run --rm -i hadolint/hadolint
