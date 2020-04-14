.PHONY: test-in-container build-generator push-generator

TEST_IMAGE=cwt-tests
TEST_DIR=test/$(TARGET)
TESTS=$(shell cd test/ && ls test_*.py)
TEST_CONTAINER_RUN=docker run --rm -it $(TEST_IMAGE)
GENERATOR_IMAGE=quay.io/rhscl/cwt-generator

.PHONY: test
test: $(TESTS)

$(TESTS):
	PYTHONPATH=.:$$PYTHONPATH python3 -W ignore::DeprecationWarning test/$@ -v

build:
	docker build --tag $(TEST_IMAGE) -f Dockerfile.tests .

test-in-container: build
	$(TEST_CONTAINER_RUN) bash -c "pip3 install .; make test"

build-generator:
	docker build --tag ${GENERATOR_IMAGE} -f Dockerfile.generator .

push-generator: build-generator
	docker push ${GENERATOR_IMAGE}
