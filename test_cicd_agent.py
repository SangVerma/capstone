import pytest
import requests
from unittest.mock import patch, MagicMock

from cicd_agent import fetch_pr_details


@patch("cicd_agent.requests.get")
def test_fetch_pr_details_success(mock_get):
    """Test that a successful GitHub API response returns the code diff."""
    # Arrange: Set up our mock response
    mock_response = MagicMock()
    mock_response.text = "diff --git a/main.py b/main.py\n+ print('hello')"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    state = {"repo_name": "vermasang/jobBot", "pr_number": 101}

    # Act
    result = fetch_pr_details(state)

    # Assert
    assert "code_diff" in result
    assert result["code_diff"] == "diff --git a/main.py b/main.py\n+ print('hello')"
    
    mock_get.assert_called_once_with(
        "https://api.github.com/repos/vermasang/jobBot/pulls/101",
        headers={"Accept": "application/vnd.github.v3.diff"},
        timeout=15
    )


@patch("cicd_agent.requests.get")
def test_fetch_pr_details_error(mock_get):
    """Test that network errors are gracefully caught and returned in the state."""
    # Arrange: Make the mock raise a RequestException
    mock_get.side_effect = requests.exceptions.RequestException("Mocked API Error")

    state = {"repo_name": "vermasang/jobBot", "pr_number": 999}

    # Act
    result = fetch_pr_details(state)

    # Assert
    assert "code_diff" in result
    assert "Error fetching diff: Mocked API Error" in result["code_diff"]


@patch("cicd_agent.os.environ.get")
@patch("cicd_agent.requests.get")
def test_fetch_pr_details_with_github_token(mock_get, mock_env_get):
    """Test that the Authorization header is added if GITHUB_TOKEN is present."""
    # Arrange
    mock_env_get.return_value = "fake_gh_token_123"
    mock_get.return_value = MagicMock(text="dummy diff")
    
    state = {"repo_name": "vermasang/jobBot", "pr_number": 101}

    # Act
    fetch_pr_details(state)

    # Assert
    mock_env_get.assert_called_with("GITHUB_TOKEN")
    
    # Extract the headers passed to requests.get
    called_args, called_kwargs = mock_get.call_args
    headers_used = called_kwargs.get("headers", {})
    
    assert "Authorization" in headers_used
    assert headers_used["Authorization"] == "Bearer fake_gh_token_123"