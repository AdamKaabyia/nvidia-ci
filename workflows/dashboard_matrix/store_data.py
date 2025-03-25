import os
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from logger import logger


ocp_data: Dict[str, List[Dict[str, Any]]] = {}

@dataclass
class TestResults:
    ocp_version: str
    gpu_version: str
    status: str
    link: str
    timestamp: str

    def to_dict(self) -> Dict[str, str]:
        """Convert TestResults object to a dictionary for easy JSON serialization."""
        return {
            "ocp": self.ocp_version,
            "gpu": self.gpu_version,
            "status": self.status,
            "link": self.link,
            "timestamp": self.timestamp
        }

# def store_ocp_data(
#     original_ocp_version: str,
#     full_ocp_version: str,
#     gpu: str,
#     status: str,
#     link: str,
#     timestamp: str
# ) -> None:
#     """Store OCP test results with both original and full versions."""
    
#     logger.info(f"[store_ocp_data] Received OCP versions: Original={original_ocp_version}, Full={full_ocp_version}")
#     logger.info(f"[store_ocp_data] GPU={gpu}, Status={status}, Link={link}, Timestamp={timestamp}")

#     # Ensure ocp_data has a list for the exact original_ocp_version
#     if original_ocp_version not in ocp_data:
#         logger.info(f"[store_ocp_data] {original_ocp_version} not in ocp_data yet; creating a new list.")
#         ocp_data[original_ocp_version] = []
#     else:
#         logger.info(f"[store_ocp_data] {original_ocp_version} already exists, appending to it.")

#     # Create a TestResults object and append it
#     test_result = TestResults(
#         ocp_version=full_ocp_version,
#         gpu_version=gpu,
#         status=status,
#         link=link,
#         timestamp=timestamp
#     )
#     ocp_data[original_ocp_version].append(test_result.to_dict())

#     # Log what was stored
#     logger.info(f"[store_ocp_data] ocp_data[{original_ocp_version}] updated with: {test_result.to_dict()}")
#     logger.info(f"[store_ocp_data] Current ocp_data keys: {list(ocp_data.keys())}")
#     logger.info(f"[store_ocp_data] ocp_data[{original_ocp_version}] length is now: {len(ocp_data[original_ocp_version])}")

def save_to_json(
    new_data: Dict[str, Any],
    output_dir: str,
    existing_data: Dict[str, Any] = None
) -> None:
    """
    Save the new_data to a JSON file (ocp_data.json) in the specified output directory.
    If existing_data is provided, merge new_data into it; otherwise, new_data is written as is.
    This function does NOT load data from disk.
    """
    file_path = os.path.join(output_dir, "ocp_data.json")
    logger.info(f"[save_to_json] Saving data to {file_path}")
    try:
        if existing_data is None:
            existing_data = {}
        # Merge new data into existing_data.
        existing_data.update(new_data)
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)
        logger.info(f"[save_to_json] Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"[save_to_json] Error saving data to {file_path}: {e}")

