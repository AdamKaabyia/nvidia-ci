# Export GO111MODULE=on to enable project to be built from within GOPATH/src
export GO111MODULE=on
GO_PACKAGES=$(shell go list ./... | grep -v vendor)
.PHONY: lint \
        deps-update \
        vet

.PHONY: mockgen
mockgen: ## Install mockgen locally.
	go install go.uber.org/mock/mockgen@v0.3.0

.PHONY: generate
generate: mockgen ## Generate code containing DeepCopy, DeepCopyInto, and DeepCopyObject method implementations.
	go generate ./...

vet:
	go vet ${GO_PACKAGES}

lint:
	@echo "Running go lint"
	scripts/golangci-lint.sh

deps-update:
	go mod tidy && \
	go mod vendor

install-ginkgo:
	scripts/install-ginkgo.sh

build-container-image:
	@echo "Building container image"
	podman build -t nvidiagpu:latest -f Containerfile

install: deps-update install-ginkgo
	@echo "Installing needed dependencies"

TEST ?= ...

.PHONY: unit-test
unit-test:
	go test github.com/rh-ecosystem-edge/nvidia-ci/$(TEST)

get-gpu-operator-must-gather:
	test -s gpu-operator-must-gather.sh || (\
    		SCRIPT_URL="https://raw.githubusercontent.com/NVIDIA/gpu-operator/v23.9.1/hack/must-gather.sh" && \
    		if ! curl -SsL -o gpu-operator-must-gather.sh -L $$SCRIPT_URL; then \
    			echo "Failed to download must-gather script" >&2; \
    			exit 1; \
    		fi && \
    		chmod +x gpu-operator-must-gather.sh \
    	)

run-tests: get-gpu-operator-must-gather
	@echo "Executing nvidiagpu test-runner script"
	scripts/test-runner.sh

test-bm-arm-deployment:
	/bin/bash tests/gpu-operator-arm-bm/uninstall-gpu-operator.sh
	/bin/bash tests/gpu-operator-arm-bm/install-gpu-operator.sh
	/bin/bash tests/gpu-operator-arm-bm/areweok.sh

############################################################################
PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
KUBECONFIG := $(PROJECT_DIR)/kubeconfig
DUMP_FAILED_TESTS := true
VERBOSE_LEVEL := 100

# Common variables
export KUBECONFIG
export DUMP_FAILED_TESTS
export VERBOSE_LEVEL

.PHONY: gpu-no-scaling gpu-with-scaling network all clean

gpu-no-scaling:
	@echo "Running NVIDIA GPU Operator Tests (No Scaling)..."
	@mkdir -p $(PROJECT_DIR)/tmp/nvidia-gpu-ci-no-scaling-logs-dir
	@export REPORTS_DUMP_DIR="$(PROJECT_DIR)/tmp/nvidia-gpu-ci-no-scaling-logs-dir"; \
	export TEST_FEATURES="nvidiagpu"; \
	export TEST_LABELS="nvidia-ci,gpu"; \
	export TEST_TRACE=false; \
	export NVIDIAGPU_GPU_MACHINESET_INSTANCE_TYPE=""; \
	export NVIDIAGPU_GPU_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/certified-operator-index:v4.16"; \
	export NVIDIAGPU_NFD_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/redhat-operator-index:v4.17"; \
	make run-tests | tee $(PROJECT_DIR)/test_nvidiagpu_no_scaling.log

gpu-with-scaling:
	@echo "Running NVIDIA GPU Operator Tests (With Scaling)..."
	@mkdir -p $(PROJECT_DIR)/tmp/nvidia-gpu-ci-with-scaling-logs-dir
	@export REPORTS_DUMP_DIR="$(PROJECT_DIR)/tmp/nvidia-gpu-ci-with-scaling-logs-dir"; \
	export TEST_FEATURES="nvidiagpu"; \
	export TEST_LABELS="nvidia-ci,gpu"; \
	export TEST_TRACE=false; \
	export NVIDIAGPU_GPU_MACHINESET_INSTANCE_TYPE="g4dn.xlarge"; \
	export NVIDIAGPU_GPU_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/certified-operator-index:v4.16"; \
	export NVIDIAGPU_NFD_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/redhat-operator-index:v4.17"; \
	make run-tests | tee $(PROJECT_DIR)/test_nvidiagpu_with_scaling.log

network:
	@echo "Running NVIDIA Network Operator Tests..."
	@mkdir -p $(PROJECT_DIR)/tmp/nvidia-nno-ci-logs-dir
	@export REPORTS_DUMP_DIR="$(PROJECT_DIR)/tmp/nvidia-nno-ci-logs-dir"; \
	export TEST_FEATURES="nvidianetwork"; \
	export TEST_LABELS="nno"; \
	export TEST_TRACE=false; \
	export NVIDIANETWORK_CATALOGSOURCE="certified-operators"; \
	export NVIDIANETWORK_SUBSCRIPTION_CHANNEL="v24.7"; \
	export NVIDIANETWORK_NNO_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/certified-operator-index:v4.16"; \
	export NVIDIANETWORK_NFD_FALLBACK_CATALOGSOURCE_INDEX_IMAGE="registry.redhat.io/redhat/redhat-operator-index:v4.17"; \
	export OFED_REPOSITORY="quay.io/bschmaus"; \
	export OFED_DRIVER_VERSION="24.10-0.5.5.0-0"; \
	make run-tests | tee $(PROJECT_DIR)/test_nvidianetwork_short.log

all: gpu-no-scaling gpu-with-scaling network

clean:
	@echo "Cleaning test logs..."
	@rm -rf $(PROJECT_DIR)/tmp/nvidia-gpu-ci-* $(PROJECT_DIR)/test_nvidiagpu_*.log
