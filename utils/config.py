"""
Configuration management utilities

Loads configuration from YAML files and environment variables.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    # Try to find config file
    if not os.path.exists(config_path):
        # Try in parent directory
        config_path = os.path.join(os.path.dirname(__file__), "..", config_path)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override with environment variables where applicable
    if os.getenv('GOOGLE_API_KEY'):
        config['google_api_key'] = os.getenv('GOOGLE_API_KEY')

    if os.getenv('LOG_LEVEL'):
        config['logging']['level'] = os.getenv('LOG_LEVEL')

    return config


def get_data_dir() -> Path:
    """Get the data directory path."""
    data_dir = Path(os.getenv('DATA_DIR', './data'))
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_incidents_dir() -> Path:
    """Get the incidents storage directory."""
    incidents_dir = Path(os.getenv('INCIDENTS_DIR', './data/incidents'))
    incidents_dir.mkdir(parents=True, exist_ok=True)
    return incidents_dir


def get_memory_bank_dir() -> Path:
    """Get the memory bank directory."""
    memory_dir = Path(os.getenv('MEMORY_BANK_DIR', './data/memory_bank'))
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir