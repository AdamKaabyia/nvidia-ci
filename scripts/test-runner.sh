#!/usr/bin/env bash

GOPATH="${GOPATH:-~/go}"
PATH=$PATH:$GOPATH/bin
TEST_DIR="./tests"

# Override REPORTS_DUMP_DIR if ARTIFACT_DIR is set
if [[ -n "${ARTIFACT_DIR}" ]]; then
    export REPORTS_DUMP_DIR=${ARTIFACT_DIR}  # export passes the variable down to child processes.
fi

# Check that TEST_FEATURES environment variable has been set
if [[ -z "${TEST_FEATURES}" ]]; then
    echo "TEST_FEATURES environment variable is undefined"
    exit 1
fi

# Initialize an empty string for storing feature directories
feature_dirs=""

# Set feature_dirs to top-level test directory when "all" feature provided
if [[ "${TEST_FEATURES}" == "all" ]]; then
    feature_dirs=${TEST_DIR}
else
    # Find all test directories matching provided features
    for feature in ${TEST_FEATURES}; do
        discovered_features=$(find $TEST_DIR -maxdepth 1 -type d -name "*${feature}*" -not -path '*/internal/*')
        if [[ -n $discovered_features ]]; then
            feature_dirs+=" $discovered_features"
        elif [[ "${VERBOSE_SCRIPT}" == "true" ]]; then
            echo "Could not find any feature directories matching ${feature}"
        fi
    done

    if [[ -z "${feature_dirs}" ]]; then
        echo "Could not find any feature directories for provided features: ${TEST_FEATURES}"
        exit 1
    fi

    if [[ "${VERBOSE_SCRIPT}" == "true" ]]; then
        echo "Found feature directories:"
        for directory in $feature_dirs; do echo "$directory"; done
    fi
fi

# Determine the ginkgo focus based on the workload
ginkgo_focus=""
if [[ "${TEST_WORKLOAD}" == "cuda-vector-add" ]]; then
    ginkgo_focus="--focus=\"CUDA Vector Add Test\""
fi

# Build ginkgo command
cmd="PATH_TO_MUST_GATHER_SCRIPT=$(pwd)/gpu-operator-must-gather.sh ginkgo -timeout=24h --keep-going --require-suite -r"

if [[ "${TEST_VERBOSE}" == "true" ]]; then
    cmd+=" -vv"
fi

if [[ "${TEST_TRACE}" == "true" ]]; then
    cmd+=" --trace"
fi

if [[ -n "${ginkgo_focus}" ]]; then
    cmd+=" ${ginkgo_focus}"
elif [[ -n "${TEST_LABELS}" ]]; then
    cmd+=" --label-filter=\"${TEST_LABELS}\""
fi

cmd+=" ${feature_dirs} $@"   # Append user args --xxx=yyy...

# Execute ginkgo command
echo "Executing command: $cmd"
eval $cmd
