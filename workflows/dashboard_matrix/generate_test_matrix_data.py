import argparse
import argparse
import urllib.parse
import requests
import re
import os
import json
import subprocess
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from logger import logger
from store_data import save_to_json  # This function now expects data as a list, plus output_dir

@dataclass
class TestResults:
    ocp_version: str
    gpu_version: str
    status: str
    link: str
    timestamp: str

    def to_dict(self) -> Dict[str, str]:
        """Convert the TestResults object to a dictionary for JSON serialization."""
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

# Regular expression for matching test pattern
TEST_PATTERN = re.compile(
    r"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/\d+/pull-ci-rh-ecosystem-edge-nvidia-ci-main-(?P<ocp_version>\d+\.\d+)-stable-nvidia-gpu-operator-e2e-(?P<gpu_version>\d+-\d+-x|master)/"
)

def generate_history() -> List[Dict[str, Any]]:
    """Process all closed PRs and accumulate their test results."""
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
            tests = fetch_pr_tests(pr_num)
            logger.info(f"Tests for PR #{pr_num}: {tests}")
            all_tests.extend(tests)
        return all_tests
    except Exception as e:
        raise_error(f"An unexpected error occurred in generate_history: {e}")

def fetch_pr_tests(pr_num: str) -> List[Dict[str, Any]]:
    """
    Fetch test results for a given PR number.
    Returns a list of test result dictionaries.
    """
    logger.info(f"Fetching tests for PR #{pr_num}")
    try:
        response = requests.get(
            url="https://storage.googleapis.com/storage/v1/b/test-platform-results/o",
            params={
                "prefix": f"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/{pr_num}/",
                "alt": "json",
                "delimiter": "/",
                "includeFoldersAsPrefixes": "True",
                "maxResults": "1000",
                "projection": "noAcl"
            },
            headers={"Accept": "application/json"}
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
            ocp: str = match.group("ocp_version")
            gpu_suffix: str = match.group("gpu_version")
            result: Dict[str, Any] = get_job_results(pr_num, job, ocp, gpu_suffix)
            logger.info(f"Test result for {job}: {result}")
            tests.append(result)
        return tests
    except Exception as e:
        raise_error(f"An unexpected error occurred in fetch_pr_tests for PR {pr_num}: {e}")
        return []

def get_job_results(pr_id: str, prefix: str, ocp_version: str, gpu_version_suffix: str) -> Dict[str, Any]:
    """
    Retrieve job results for a given test job.
    Returns a dictionary with key details and updates the provided ocp_data.
    """
    try:
        logger.info(f"Fetching job results for {prefix}")
        response = requests.get(
            url="https://storage.googleapis.com/storage/v1/b/test-platform-results/o",
            params={
                "prefix": prefix,
                "alt": "json",
                "delimiter": "/",
                "includeFoldersAsPrefixes": "True",
                "maxResults": "1000",
                "projection": "noAcl"
            },
            headers={"Accept": "application/json"}
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
        else:
            result["gpu_version"] = gpu_suffix_to_version(gpu_version_suffix)
        return result
    except requests.exceptions.RequestException as e:
        raise_error(f"Request failed in get_job_results: {e}")
    except KeyError as e:
        raise_error(f"Missing expected field in job result: {e}")
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_job_results: {e}")
        return {}

def gpu_suffix_to_version(gpu: str) -> str:
    return gpu if gpu == "master" else gpu[:-2].replace("-", ".")

def get_job_url(pr_id: str, ocp_minor: str, gpu_suffix: str, job_id: str) -> str:
    return (
        f"https://prow.ci.openshift.org/view/gs/test-platform-results/pr-logs/"
        f"pull/rh-ecosystem-edge_nvidia-ci/{pr_id}/pull-ci-rh-ecosystem-edge-nvidia-ci-main-"
        f"{ocp_minor}-stable-nvidia-gpu-operator-e2e-{gpu_suffix}/{job_id}"
    )

def get_versions(prefix: str, build_id: str, gpu_version_suffix: str) -> Tuple[str, str]:
    try:
        logger.info(f"Fetching versions for build {build_id}")
        ocp_version_file = f"{prefix}{build_id}/artifacts/nvidia-gpu-operator-e2e-{gpu_version_suffix}/" \
                           f"gpu-operator-e2e/artifacts/ocp.version"
        ocp_version: str = fetch_file_content(ocp_version_file)
        gpu_version_file = f"{prefix}{build_id}/artifacts/nvidia-gpu-operator-e2e-{gpu_version_suffix}/" \
                           f"gpu-operator-e2e/artifacts/operator.version"
        gpu_version: str = fetch_file_content(gpu_version_file)
        return (ocp_version, gpu_version)
    except requests.exceptions.RequestException as e:
        raise_error(f"Request failed in get_versions: {e}")
    except KeyError as e:
        raise_error(f"Missing expected field in version fetch: {e}")
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_versions: {e}")
        return ("", "")

def fetch_file_content(file_path: str) -> str:
    try:
        logger.info(f"Fetching file content for {file_path}")
        response = requests.get(
            url=f"https://storage.googleapis.com/storage/v1/b/test-platform-results/o/{urllib.parse.quote_plus(file_path)}",
            params={"alt": "media"}
        )
        response.raise_for_status()
        return response.content.decode("UTF-8")
    except requests.exceptions.RequestException as e:
        raise_error(f"Request failed in fetch_file_content: {e}")
    except Exception as e:
        raise_error(f"An unexpected error occurred in fetch_file_content: {e}")
        return ""

def get_status(prefix: str, latest_build_id: str) -> Tuple[str, Any]:
    try:
        logger.info(f"Fetching status for {latest_build_id}")
        finished_file = f"{prefix}{latest_build_id}/finished.json"
        response = requests.get(
            url=f"https://storage.googleapis.com/storage/v1/b/test-platform-results/o/{urllib.parse.quote_plus(finished_file)}",
            params={"alt": "media"}
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        status: str = data.get("result", "UNKNOWN")
        timestamp = data.get("timestamp", None)
        return status, timestamp
    except requests.exceptions.RequestException as e:
        raise_error(f"Request failed in get_status: {e}")
    except KeyError as e:
        raise_error(f"Missing expected field in finished.json response: {e}")
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_status: {e}")
        return ("UNKNOWN", None)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test matrix data")
    parser.add_argument("--pr", default="all", help="PR number to process; use 'all' to process all history")
    parser.add_argument("--process_mode", default="last", choices=["last", "all"],
                        help="Processing mode: 'last' to process only the last PR or 'all' to process all history")
    parser.add_argument("--output_dir", required=True, help="Output directory where JSON and HTML are stored")
    parser.add_argument("--branch", default="gh-pages",
                        help="Branch from which to extract existing JSON data")
    args = parser.parse_args()

    logger.info(f"Arguments received: PR={args.pr}, process_mode={args.process_mode}, output_dir={args.output_dir}, branch={args.branch}")

    # Extract existing JSON data from a different branch using git.
    try:
        old_data_json = subprocess.check_output(["git", "show", f"{args.branch}:ocp_data.json"])
        old_data: List[Dict[str, Any]] = json.loads(old_data_json)
        logger.info(f"Loaded existing data with {len(old_data)} records.")
    except Exception as e:
        logger.info("No existing JSON data found in the specified branch; starting with empty data.")
        old_data = []

    # Fetch new test data.
    if args.pr.lower() == "all":
        new_data = generate_history()
    else:
        new_data = fetch_pr_tests(args.pr, {})  # Pass an empty dict if not grouping by OCP.

    # Merge the existing data with new data.
    merged_data = old_data + new_data

    # Save the merged data to the output directory.
    save_to_json(merged_data, args.output_dir)

if __name__ == "__main__":
    main()
