.PHONY: test-in-container

TEST_IMAGE=cwt-tests
TEST_DIR=test/$(TARGET)
TESTS=$(shell cd test/ && ls test_*)
TEST_CONTAINER_RUN=docker run --rm -it -v $(CURDIR):/cwt $(TEST_IMAGE)

.PHONY: test
test: $(TESTS)

$(TESTS):
	PYTHONPATH=.:$$PYTHONPATH python3 -W ignore::DeprecationWarning test/$@ -v

build:
	docker build --tag $(TEST_IMAGE) -f Dockerfile.tests .

test-in-container: build
	$(TEST_CONTAINER_RUN) bash -c "pip3 install .; make test"
