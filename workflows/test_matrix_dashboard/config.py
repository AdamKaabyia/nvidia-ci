import re

# Base URL for the storage API
BASE_URL = "https://storage.googleapis.com/storage/v1/b/test-platform-results/o"

# Regular expression to match test result paths
TEST_PATTERN = re.compile(
    r"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/\d+/pull-ci-rh-ecosystem-edge-nvidia-ci-main-(?P<ocp_version>\d+\.\d+)-stable-nvidia-gpu-operator-e2e-(?P<gpu_version>\d+-\d+-x|master)/"
)
