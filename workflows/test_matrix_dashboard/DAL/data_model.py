from dataclasses import dataclass
from typing import Any, Dict


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

