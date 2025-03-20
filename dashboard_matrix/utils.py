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

def store_ocp_data(original_ocp_version, full_ocp_version, gpu, status, link,timestamp):
    """Store OCP test results with both original and full versions."""
    
    logger.info(f"Received OCP versions: Original={original_ocp_version}, Full={full_ocp_version}")

    # Ensure ocp_data has a list for the exact full_ocp_version
    if original_ocp_version not in ocp_data:
        ocp_data[original_ocp_version] = []

    # Create a TestResults object and append it to the full_ocp_version key
    test_result = TestResults(ocp_version=full_ocp_version, gpu_version=gpu, status=status, link=link, timestamp=timestamp)
    ocp_data[original_ocp_version].append(test_result.to_dict())

    # Log what was stored
    logger.info(f"Stored OCP version: {full_ocp_version} - GPU: {gpu}, Status: {status}, Link: {link}")


def save_to_json(file_path='ocp_data.json'):
    """Save the collected data to a JSON file, preserving old data."""
    try:
        # Load existing data if the file exists
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Update the existing data with the new ocp_data
        existing_data.update(ocp_data)

        # Save the combined data to the file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)

        logger.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")


