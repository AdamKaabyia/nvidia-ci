import urllib.parse
from typing import Any, Dict, List, Tuple

from DAL.store_data import update_ocp_data
from helpers.config import BASE_URL
from helpers.http_helpers import fetch_file_content, make_request
from helpers.logger import logger
from helpers.utils import raise_error


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

        params = {
            "prefix": prefix,
            "alt": "json",
            "delimiter": "/",
            "includeFoldersAsPrefixes": "True",
            "maxResults": "1000",
            "projection": "noAcl",
        }
        headers = {"Accept": "application/json"}
        response_data = make_request(BASE_URL, params=params, headers=headers)
        latest_build: str = fetch_file_content(response_data["items"][0]["name"])
        logger.info(f"Job {prefix}: latest build is {latest_build}")
        status, timestamp = get_status_and_time(prefix, latest_build)
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


def get_status_and_time(prefix: str, latest_build_id: str) -> Tuple[str, Any]:
    logger.info(f"Fetching status for {latest_build_id}")
    try:
        finished_file = f"{prefix}{latest_build_id}/finished.json"
        url = f"{BASE_URL}/{urllib.parse.quote_plus(finished_file)}"
        data: Dict[str, Any] = make_request(url, params={"alt": "media"})
        status: str = data.get("result", "UNKNOWN")
        timestamp = data.get("timestamp", None)
        return status, timestamp
    except Exception as e:
        raise_error(f"An unexpected error occurred in get_status_and_time: {e}")
        
