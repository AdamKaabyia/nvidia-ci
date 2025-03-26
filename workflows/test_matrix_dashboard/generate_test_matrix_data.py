import argparse
import json
from typing import Any, Dict, List

from config import BASE_URL, TEST_PATTERN
from get_test_data import get_job_results
from http_helpers import make_request
from logger import logger
from store_data import save_to_json
from utils import raise_error


def retrieve_all_prs(ocp_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Process all closed PRs and update ocp_data with their test results.
    Returns a list of test result dictionaries.
    """
    logger.info("Generating history...")
    try:
        url = "https://api.github.com/repos/rh-ecosystem-edge/nvidia-ci/pulls"
        params = {"state": "closed", "base": "main", "per_page": "100", "page": "1"}
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        response_data = make_request(url, params=params, headers=headers)
        
        all_tests: List[Dict[str, Any]] = []
        for pr in response_data:
            pr_num = str(pr["number"])
            logger.info(f"Processing PR #{pr_num}")
            tests = get_all_pr_tests(pr_num, ocp_data)
            logger.info(f"Tests for PR #{pr_num}: {tests}")
            all_tests.extend(tests)
        return all_tests
    except Exception as e:
        raise_error(f"An unexpected error occurred in retrieve_all_prs: {e}")

def get_all_pr_tests(pr_num: str, ocp_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Fetch test results for the given PR number and update ocp_data with those results.
    Returns a list of test result dictionaries.
    """
    logger.info(f"Getting all tests for PR #{pr_num}")
    try:
        params = {
            "prefix": f"pr-logs/pull/rh-ecosystem-edge_nvidia-ci/{pr_num}/",
            "alt": "json",
            "delimiter": "/",
            "includeFoldersAsPrefixes": "True",
            "maxResults": "1000",
            "projection": "noAcl",
        }
        headers = {"Accept": "application/json"}
        response_data = make_request(BASE_URL, params=params, headers=headers)
        prefixes = response_data.get("prefixes")
        
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



def main() -> None:
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
        new_data = retrieve_all_prs(local_ocp_data)
    else:
        new_data = get_all_pr_tests(args.pr, local_ocp_data)
        logger.info(f"Tests for PR {args.pr}: {new_data}")

    # At this point, local_ocp_data has been updated by the functions.
    # Save the updated ocp_data dictionary to the output directory.
    save_to_json(local_ocp_data, args.output_dir)

if __name__ == "__main__":
    main()
