import os
import json
import requests
import re
import urllib.parse
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from logger import logger

TEST_PATTERN = re.compile(
    r"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/\d+/pull-ci-rh-ecosystem-edge-nvidia-ci-main-(?P<ocp_version>\d+\.\d+)-stable-nvidia-gpu-operator-e2e-(?P<gpu_version>\d+-\d+-x|master)/"
)

@dataclass
class TestResults:
    ocp_version: str
    gpu_version: str
    status: str
    link: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert TestResults object to a dictionary for JSON serialization."""
        return {
            "ocp": self.ocp_version,
            "gpu": self.gpu_version,
            "status": self.status,
            "link": self.link,
            "timestamp": self.timestamp,
        }

def raise_error(message: str) -> None:
    logger.error(message)
    raise Exception(message)

def update_ocp_data(
    ocp_data: Dict[str, List[Dict[str, Any]]],
    original_ocp_version: str,
    full_ocp_version: str,
    gpu: str,
    status: str,
    link: str,
    timestamp: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Update the ocp_data dictionary with new test results for the given OCP version
    and return the updated dictionary.
    """
    logger.info(f"[update_ocp_data] Received: Original={original_ocp_version}, Full={full_ocp_version}, GPU={gpu}, Status={status}")
    ocp_data.setdefault(original_ocp_version, []).append(
        TestResults(full_ocp_version, gpu, status, link, timestamp).to_dict()
    )
    logger.info(f"[update_ocp_data] ocp_data[{original_ocp_version}] now has {len(ocp_data[original_ocp_version])} items.")
    return ocp_data

def save_to_json(
    data: Dict[str, Any],
    output_dir: str,
    existing_data: Dict[str, Any] = None,
) -> None:
    """
    Save the data dictionary to a JSON file (ocp_data.json) in the specified output directory.
    If existing_data is provided, merge data into it; otherwise, write data as is.
    This function does NOT load data from disk.
    """
    file_path = os.path.join(output_dir, "ocp_data.json")
    logger.info(f"[save_to_json] Saving data to {file_path}")
    try:
        if existing_data is None:
            existing_data = {}
        existing_data.update(data)
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)
        logger.info(f"[save_to_json] Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"[save_to_json] Error saving data to {file_path}: {e}")

def generate_history(ocp_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Process all closed PRs and update ocp_data with their test results.
    Returns a list of test result dictionaries.
    """
    logger.info("Generating history...")
    try:
        response = requests.get(
            url="https://api.github.com/repos/rh-ecosystem-edge/nvidia-ci/pulls",
            params={"state": "closed", "base": "main", "per_page": "100", "page": "1"},
            headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        )
        response.raise_for_status()
        all_tests: List[Dict[str, Any]] = []
        for pr in response.json():
            pr_num = str(pr["number"])
            logger.info(f"Processing PR #{pr_num}")
            tests = get_all_pr_tests(pr_num, ocp_data)
            logger.info(f"Tests for PR #{pr_num}: {tests}")
            all_tests.extend(tests)
        return all_tests
    except Exception as e:
        raise_error(f"An unexpected error occurred in generate_history: {e}")

def get_all_pr_tests(pr_num: str, ocp_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Fetch test results for the given PR number and update ocp_data with those results.
    Returns a list of test result dictionaries.
    """
    logger.info(f"Getting all tests for PR #{pr_num}")
    try:
        response = requests.get(
            url="https://storage.googleapis.com/storage/v1/b/test-platform-results/o",
            params={
                "prefix": f"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/{pr_num}/",
                "alt": "json",
                "delimiter": "/",
                "includeFoldersAsPrefixes": "True",
                "maxResults": "1000",
                "projection": "noAcl",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        prefixes = response.json().get("prefixes")
        tests: List[Dict[str, Any]] = []
        if not prefixes:
            return tests
        for job in prefixes:
            match = TEST_PATTERN.match(job)
            if not match:
                continue
            ocp = match.group("ocp_version")
            gpu_suffix = match.group("gpu_version")
            result: Dict[str, Any] = get_job_results(pr_num, job, ocp, gpu_suffix, ocp_data)
            logger.info(f"Test result for {job}: {result}")
            tests.append(result)
        return tests
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_all_pr_tests for PR {pr_num}: {e}")


def get_job_results(
    pr_id: str, prefix: str, ocp_version: str, gpu_version_suffix: str,
    ocp_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Retrieve job results for a given test job, update ocp_data with the result,
    and return a dictionary with key details.
    """
    logger.info(f"Getting job results for {prefix}")
    try:
        response = requests.get(
            url="https://storage.googleapis.com/storage/v1/b/test-platform-results/o",
            params={
                "prefix": prefix,
                "alt": "json",
                "delimiter": "/",
                "includeFoldersAsPrefixes": "True",
                "maxResults": "1000",
                "projection": "noAcl",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        latest_build: str = fetch_file_content(response.json()["items"][0]["name"])
        logger.info(f"Job {prefix}: latest build is {latest_build}")
        status, timestamp = get_status(prefix, latest_build)
        job_url: str = get_job_url(pr_id, ocp_version, gpu_version_suffix, latest_build)
        result: Dict[str, Any] = {
            "prefix": prefix,
            "ocp_version": ocp_version,
            "status": status,
            "timestamp": timestamp,
            "url": job_url,
        }
        if status == "SUCCESS":
            exact_versions: Tuple[str, str] = get_versions(prefix, latest_build, gpu_version_suffix)
            result["exact_ocp_version"] = exact_versions[0]
            result["exact_gpu_version"] = exact_versions[1]
            result["gpu_version"] = gpu_version_suffix
            # Pass the ocp_data dictionary as the first argument
            update_ocp_data(ocp_data, ocp_version, exact_versions[0], gpu_version_suffix, status, job_url, timestamp)
        else:
            result["gpu_version"] = gpu_suffix_to_version(gpu_version_suffix)
            update_ocp_data(ocp_data, ocp_version, ocp_version, gpu_suffix_to_version(gpu_version_suffix), status, job_url, timestamp)
        return result
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_job_results: {e}")


def gpu_suffix_to_version(gpu: str) -> str:
    return gpu if gpu == "master" else gpu[:-2].replace("-", ".")

def get_job_url(pr_id: str, ocp_minor: str, gpu_suffix: str, job_id: str) -> str:
    return (
        f"https://prow.ci.openshift.org/view/gs/test-platform-results/pr-logs/"
        f"pull/rh-ecosystem-edge_nvidia-ci/{pr_id}/pull-ci-rh-ecosystem-edge-nvidia-ci-main-"
        f"{ocp_minor}-stable-nvidia-gpu-operator-e2e-{gpu_suffix}/{job_id}"
    )

def get_versions(prefix: str, build_id: str, gpu_version_suffix: str) -> Tuple[str, str]:
    logger.info(f"Fetching versions for build {build_id}")
    try:
        ocp_version_file = f"{prefix}{build_id}/artifacts/nvidia-gpu-operator-e2e-{gpu_version_suffix}/" \
                           f"gpu-operator-e2e/artifacts/ocp.version"
        ocp_version: str = fetch_file_content(ocp_version_file)
        gpu_version_file = f"{prefix}{build_id}/artifacts/nvidia-gpu-operator-e2e-{gpu_version_suffix}/" \
                           f"gpu-operator-e2e/artifacts/operator.version"
        gpu_version: str = fetch_file_content(gpu_version_file)
        return (ocp_version, gpu_version)
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_versions: {e}")

def fetch_file_content(file_path: str) -> str:
    logger.info(f"Fetching file content for {file_path}")
    try:
        response = requests.get(
            url=f"https://storage.googleapis.com/storage/v1/b/test-platform-results/o/{urllib.parse.quote_plus(file_path)}",
            params={"alt": "media"},
        )
        response.raise_for_status()
        return response.content.decode("UTF-8")
    except Exception as e:
        raise_error(f"An unexpected error occurred in fetch_file_content: {e}")
        return ""

def get_status(prefix: str, latest_build_id: str) -> Tuple[str, Any]:
    logger.info(f"Fetching status for {latest_build_id}")
    try:
        finished_file = f"{prefix}{latest_build_id}/finished.json"
        response = requests.get(
            url=f"https://storage.googleapis.com/storage/v1/b/test-platform-results/o/{urllib.parse.quote_plus(finished_file)}",
            params={"alt": "media"},
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        status: str = data.get("result", "UNKNOWN")
        timestamp = data.get("timestamp", None)
        return status, timestamp
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_status: {e}")
        

def main() -> None:
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Generate test matrix data")
    parser.add_argument("--pr", default="all", help="PR number to process; use 'all' to process all history")
    parser.add_argument("--output_dir", required=True, help="Output directory where JSON and HTML are stored")
    parser.add_argument("--old_data_file", required=True,
                        help="Path to the existing ocp_data.json file (from another branch)")
    args = parser.parse_args()

    logger.info(f"Arguments received: PR={args.pr}, output_dir={args.output_dir}, old_data_file={args.old_data_file}")

    # Load the old data from the provided file.
    try:
        with open(args.old_data_file, "r") as f:
            old_data: Dict[str, List[Dict[str, Any]]] = json.load(f)
        logger.info(f"Loaded old data with keys: {list(old_data.keys())}")
    except Exception as e:
        logger.info("No old data found; starting with empty data.")
        old_data = {}

    # Create a local ocp_data dictionary initialized with the old data.
    local_ocp_data: Dict[str, List[Dict[str, Any]]] = old_data.copy()

    # Fetch new test data.
    if args.pr.lower() == "all":
        new_data = generate_history(local_ocp_data)
    else:
        new_data = get_all_pr_tests(args.pr, local_ocp_data)
        logger.info(f"Tests for PR {args.pr}: {new_data}")

    # At this point, local_ocp_data has been updated by the functions.
    # Save the updated ocp_data dictionary to the output directory.
    save_to_json(local_ocp_data, args.output_dir)

if __name__ == "__main__":
    main()
