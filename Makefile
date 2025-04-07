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
	docker run --rm -i hadolint/hadolint < images/Python/Dockerfile

dlint_r:
	@echo "Lint R Dockerfile"
	docker run --rm -i hadolint/hadolint < images/R/Dockerfile
