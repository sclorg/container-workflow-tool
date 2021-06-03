.PHONY: test-in-container build-generator push-generator

TEST_IMAGE=cwt-tests
TEST_CONTAINER_RUN=docker run --rm -it $(TEST_IMAGE)
GENERATOR_IMAGE=quay.io/rhscl/cwt-generator

.PHONY: test
test:
	PYTHONPATH=.:$$PYTHONPATH python3 -W ignore::DeprecationWarning -m unittest -v

build:
	docker build --tag $(TEST_IMAGE) -f Dockerfile.tests .

test-in-container:
	$(TEST_CONTAINER_RUN)

build-generator:
	docker build --tag ${GENERATOR_IMAGE} -f Dockerfile.generator .

push-generator: build-generator
	docker push ${GENERATOR_IMAGE}
