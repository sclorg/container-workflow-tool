TEST_DIR=test/$(TARGET)
TESTS=$(shell ls $(TEST_DIR)/test_* | xargs basename -s .py | xargs)

.PHONY: test
test: $(TESTS)

$(TESTS):
	PYTHONPATH=.:$$PYTHONPATH python3 -W ignore::DeprecationWarning $(TEST_DIR)/$@.py -v
