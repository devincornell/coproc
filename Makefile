
uninstall:
	pip uninstall -y conproc

TESTS_FOLDER = tests/
pytest: uninstall
	# tests from tests folder
	pytest $(TESTS_FOLDER)/test_*.py

TMP_TEST_FOLDER = tmp_test_deleteme
test_examples: uninstall

	# make temporary testing folder and copy files into it
	-rm -r $(TMP_TEST_FOLDER)
	mkdir $(TMP_TEST_FOLDER)
	cp $(EXAMPLES_FOLDER)/*.ipynb $(TMP_TEST_FOLDER)
	cp $(EXAMPLES_FOLDER)/*.py $(TMP_TEST_FOLDER)
	
	# convert notebooks to .py scripts
	jupyter nbconvert --to script $(TMP_TEST_FOLDER)/*.ipynb
	
	# execute example files to make sure they work

	# examples
	cd $(TMP_TEST_FOLDER); python workerresource_examples.py

	# cleanup temp folder
	-rm -r $(TMP_TEST_FOLDER)

test: pytest test_examples
tests: test # alias	
