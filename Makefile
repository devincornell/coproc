
######################## Building ########################

PACKAGE_NAME = coproc
PACKAGE_FOLDER = $(PACKAGE_NAME)/
build:
	# install latest version of compiler software
	pip install --user --upgrade setuptools wheel
	
	# actually set up package
	python setup.py sdist bdist_wheel
	
	git add setup.cfg setup.py LICENSE README.md

reinstall:
	pip uninstall -y coproc
	pip install .

uninstall:
	pip uninstall -y coproc

install:
	pip install .

######################## Testing ########################
uninstall:
	pip uninstall -y conproc

TESTS_FOLDER = tests/
pytest: uninstall
	# tests from tests folder
	cd $(TESTS_FOLDER); pytest test_*.py
	#pytest $(TESTS_FOLDER)/test_*.py

TMP_TEST_FOLDER = tmp_test_deleteme
test_examples: uninstall

	# make temporary testing folder and copy files into it
	-rm -r $(TMP_TEST_FOLDER)
	mkdir $(TMP_TEST_FOLDER)
	cp $(EXAMPLES_FOLDER)/*.ipynb $(TMP_TEST_FOLDER)
	cp $(EXAMPLES_FOLDER)/*.py $(TMP_TEST_FOLDER)
	
	# convert notebooks to .py scripts
	#jupyter nbconvert --to script $(TMP_TEST_FOLDER)/*.ipynb
	
	# execute example files to make sure they work

	# examples
	#cd $(TMP_TEST_FOLDER); python test_monitor.py

	# cleanup temp folder
	-rm -r $(TMP_TEST_FOLDER)

test: pytest test_examples
tests: test # alias	
