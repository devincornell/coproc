
PACKAGE_NAME = coproc
PACKAGE_FOLDER = $(PACKAGE_NAME)/

PDOC_TARGET_FOLDER = ./site/api/ # pdoc html files will be placed here

EXAMPLE_NOTEBOOK_FOLDER = ./examples/# this is where example notebooks are stored
EXAMPLE_NOTEBOOK_MARKDOWN_FOLDER = ./docs/examples/# this is where example notebooks are stored
EXAMPLE_NOTEBOOK_HTML_FOLDER = ./site/example_notebooks/# this is where example notebooks are stored

TESTS_FOLDER = ./tests/ # all pytest files are here

# examples
# make install
# make uninstall
# make docs
# make tests
# make build

# make clean (deletes all doc files)
# make test (runs unit tests in tests/ and exports notebooks in examples/ and tries to run them)
# make build (actually builds the python package)
# make deploy (actually builds package)


requirements:
	pip freeze > requirements.txt
	git add requirements.txt
	
	pip list > packages.txt
	git add packages.txt

#################### TO DEPLOY INSTRUCTIONS ###########################
#make test
#make clean
#make docs
#make build
#make deploy


# toplevel (run when enters 'make' without args)
all: docs build
	git add Makefile

final_check: docs build test
	@echo "ran final check"

push_all: 
	git commit -a -m '[auto_pushed_from_Makefile]'
	git push

reinstall:
	pip uninstall -y doctable
	pip install .

uninstall:
	pip uninstall -y doctable

install:
	pip install .


########################################## BUILD AND DEPLOY ################################
build:
	# install latest version of compiler software
	pip install --user --upgrade setuptools wheel
	
	# actually set up package
	python setup.py sdist bdist_wheel
	
	git add setup.cfg setup.py LICENSE
	
clean_build:
	-rm -r build
	-rm -r dist
	-rm -r $(PACKAGE_NAME).egg-info

deploy: build requirements
	# mostly pulled from https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56
	#also this: https://packaging.python.org/tutorials/packaging-projects/
	
	# first make sure deploy package is activated
	pip install --user --upgrade twine
	
	# create a source distribution
	python setup.py sdist
	
	# here we go now upload
	python -m twine upload dist/*
	

################################# CREATE DOCUMENTATION ##############################

docs: mkdocs pdoc requirements
	git add -f --all site/*
	git add --all docs/*
	# git add requirements.txt

mkdocs: example_notebooks
	mkdocs build
	cp README.md docs/index.md
	mkdocs gh-deploy

server_mkdocs:
	mkdocs serve -a localhost:8882

pdoc:
	-mkdir $(PDOC_TARGET_FOLDER)
	# pdoc --docformat google -o $(PDOC_TARGET_FOLDER) $(PACKAGE_FOLDER)

example_notebooks:
	-mkdir $(EXAMPLE_NOTEBOOK_HTML_FOLDER)
	jupyter nbconvert --to html $(EXAMPLE_NOTEBOOK_FOLDER)/*.ipynb
	mv $(EXAMPLE_NOTEBOOK_FOLDER)/*.html $(EXAMPLE_NOTEBOOK_HTML_FOLDER)

	-mkdir $(EXAMPLE_NOTEBOOK_MARKDOWN_FOLDER)
	jupyter nbconvert --to markdown $(EXAMPLE_NOTEBOOK_FOLDER)/*.ipynb
	mv $(EXAMPLE_NOTEBOOK_FOLDER)/*.md $(EXAMPLE_NOTEBOOK_MARKDOWN_FOLDER)
	
add_docs:
	git add --all $(PDOC_TARGET_FOLDER)
	git add --all $(EXAMPLE_NOTEBOOK_HTML_FOLDER)
	git add --all $(EXAMPLE_NOTEBOOK_MARKDOWN_FOLDER)

clean_docs:
	-rm -r $(PDOC_TARGET_FOLDER)
	-rm -r $(EXAMPLE_NOTEBOOK_HTML_FOLDER)
	-rm -r $(EXAMPLE_NOTEBOOK_MARKDOWN_FOLDER)

######################################## RUN TESTS ########################################

test: pytest test_examples clean_tests requirements
tests: test # alias	

pytest: uninstall
	# tests from tests folder
	cd $(TESTS_FOLDER); pytest ./*.py


TMP_TEST_FOLDER = tmp_test_deleteme
test_examples: uninstall
	# make temporary testing folder and copy files into it
	-mkdir $(TMP_TEST_FOLDER)
	cp $(EXAMPLE_NOTEBOOK_FOLDER)/*.ipynb $(TMP_TEST_FOLDER)
	-cp $(EXAMPLE_NOTEBOOK_FOLDER)/*.py $(TMP_TEST_FOLDER)
	
	# convert notebooks to .py scripts
	jupyter nbconvert --to python $(TMP_TEST_FOLDER)/*.ipynb
	
	# execute example files to make sure they work

	# THESE NOTEBOOKS WILL BE TESTED
	# cd $(TMP_TEST_FOLDER); python ex_basics.py
	# cd $(TMP_TEST_FOLDER); 

	cd $(TMP_TEST_FOLDER); \
		for FILE in *.py; do \
			echo "testing $$FILE"; \
			python $$FILE; \
		done

clean_tests:
	# cleanup temp folder
	-rm -r $(TMP_TEST_FOLDER)
	
	
################################ CLEAN ####################################

clean: clean_tests clean_docs clean_build


	
