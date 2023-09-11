# Performs an approximation of the pipeline

pipeline: prepare-sources build test

prepare-sources:
	docker build --output=out --target=just-sources --build-arg MODE=newlib --build-arg TARGET=rv64gc-lp64d --build-arg MULTILIB=non-multilib .

build:
	docker build --output=out --target=just-build --build-arg MODE=newlib --build-arg TARGET=rv64gc-lp64d --build-arg MULTILIB=non-multilib . 2>&1 | tee build.log

test:
	docker build --output=out --target=just-test --build-arg MODE=newlib --build-arg TARGET=rv64gc-lp64d --build-arg MULTILIB=non-multilib . 2>&1 | tee test.log
	cat out/testsuite.log

build-test: build test
