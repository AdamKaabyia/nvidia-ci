import json
import os
from typing import Any, Dict, List

from data_model import TestResults
from logger import logger


def update_ocp_data(
    ocp_data: Dict[str, List[Dict[str, Any]]],
    original_ocp_version: str,
    full_ocp_version: str,
    gpu: str,
    status: str,
    link: str,
    timestamp: str,
) -> None:
    """
    Update the ocp_data dictionary with new test results for the given OCP version
    and return the updated dictionary.
    """
    logger.info(f"[update_ocp_data] Received: Original={original_ocp_version}, Full={full_ocp_version}, GPU={gpu}, Status={status}")
    ocp_data.setdefault(original_ocp_version, []).append(
        TestResults(full_ocp_version, gpu, status, link, timestamp).to_dict()
    )
    logger.info(f"[update_ocp_data] ocp_data[{original_ocp_version}] now has {len(ocp_data[original_ocp_version])} items.")

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
