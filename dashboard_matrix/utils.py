import os
import json
from dataclasses import dataclass
from logger import logger

# Initialize a dictionary to store results
ocp_data = {}

@dataclass
class TestResults:
    ocp_version: str
    gpu_version: str
    status: str
    link: str
    timestamp: str

    def to_dict(self):
        """Convert TestResults object to a dictionary for easy JSON serialization."""
        return {
            "ocp": self.ocp_version,
            "gpu": self.gpu_version,
            "status": self.status,
            "link": self.link,
            "timestamp": self.timestamp
        }

def store_ocp_data(original_ocp_version, full_ocp_version, gpu, status, link, timestamp):
    """Store OCP test results with both original and full versions."""
    
    logger.info(f"[store_ocp_data] Received OCP versions: Original={original_ocp_version}, Full={full_ocp_version}")
    logger.info(f"[store_ocp_data] GPU={gpu}, Status={status}, Link={link}, Timestamp={timestamp}")

    # Ensure ocp_data has a list for the exact original_ocp_version
    if original_ocp_version not in ocp_data:
        logger.info(f"[store_ocp_data] {original_ocp_version} not in ocp_data yet; creating a new list.")
        ocp_data[original_ocp_version] = []
    else:
        logger.info(f"[store_ocp_data] {original_ocp_version} already exists, appending to it.")

    # Create a TestResults object and append it
    test_result = TestResults(
        ocp_version=full_ocp_version,
        gpu_version=gpu,
        status=status,
        link=link,
        timestamp=timestamp
    )
    ocp_data[original_ocp_version].append(test_result.to_dict())

    # Log what was stored
    logger.info(f"[store_ocp_data] ocp_data[{original_ocp_version}] updated with: {test_result.to_dict()}")
    logger.info(f"[store_ocp_data] Current ocp_data keys: {list(ocp_data.keys())}")
    logger.info(f"[store_ocp_data] ocp_data[{original_ocp_version}] length is now: {len(ocp_data[original_ocp_version])}")


def save_to_json(file_path='ocp_data.json'):
    """Save the collected data to a JSON file, preserving old data."""
    logger.info(f"[save_to_json] Attempting to save data to {file_path}")
    try:
        # Load existing data if the file exists
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
            logger.info(f"[save_to_json] Successfully loaded existing data from {file_path}.")
            logger.info(f"[save_to_json] Existing data keys: {list(existing_data.keys())}")
        except FileNotFoundError:
            existing_data = {}
            logger.info(f"[save_to_json] {file_path} not found, starting with empty {}.")

        # Debug: Print the new data keys and length
        logger.info(f"[save_to_json] New data to merge (ocp_data) keys: {list(ocp_data.keys())}")

        # Update the existing data with the new ocp_data
        existing_data.update(ocp_data)

        # Debug: Print final merged data shape
        logger.info(f"[save_to_json] Final merged data keys: {list(existing_data.keys())}")

        # Save the combined data to the file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)

        logger.info(f"[save_to_json] Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"[save_to_json] Error saving data to {file_path}: {e}")
