"""Test configuration and fixtures."""

import pytest

from rag_system.config.settings import Settings, reset_settings


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset global settings before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def settings():
    """Create a test Settings instance."""
    return Settings()
