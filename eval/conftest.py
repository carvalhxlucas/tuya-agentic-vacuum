"""
Pytest configuration for the eval suite.
Mocks the Tuya API so tests run without a real device or credentials.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture(scope="session", autouse=True)
def mock_tuya():
    """Prevents any real Tuya API calls during evaluation."""
    mock_client = MagicMock()
    mock_client.post.return_value = {"success": True, "result": True}
    mock_client.get.return_value = {"success": True, "result": []}

    with patch("agent.tools._get_tuya_client", return_value=(mock_client, "mock_device_id")):
        yield


@pytest.fixture(scope="session")
def agent():
    from agent.runner import create_agent
    return create_agent()
