"""Scenario tests: blacklist permission enforcement (specification requirements).

Per the specification:
- When the blacklist file exists its permissions must be 600 (owner read/write only).
- If permissions do not match, error code 1008 is returned and loading is refused.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import BlacklistManager


def test_scenario_blacklist_permission_600():
    """Scenario: blacklist file permission is enforced as 600.

    Specification:
    - WHEN the blacklist file exists
    - THEN its permissions must be 600 (owner read/write only)
    - AND if permissions do not match, error code 1008 is returned
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("/dev/ttyUSB0\n")
        test_path = Path(f.name)

    try:
        # Scenario 1: correct permissions (600) — should succeed
        os.chmod(test_path, 0o600)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True

        # Scenario 2: incorrect permissions (644) — should raise a permission error
        os.chmod(test_path, 0o644)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            with pytest.raises(PermissionError) as exc:
                BlacklistManager()
            assert "1008" in str(exc.value)

        # Scenario 3: incorrect permissions (777) — should raise a permission error
        os.chmod(test_path, 0o777)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            with pytest.raises(PermissionError) as exc:
                BlacklistManager()
            assert "1008" in str(exc.value)

    finally:
        os.unlink(test_path)


def test_scenario_config_permission_600():
    """Scenario: config file permission is enforced as 600.

    Specification:
    - WHEN the config file exists
    - THEN its permissions must be 600 (owner read/write only)
    - AND if permissions do not match, loading is refused (error code 1008 or logged)

    Note: ConfigManager falls back to defaults on a permission error during __init__.
    The permission error surfaces explicitly via reload().
    """
    from uart_mcp.config import ConfigManager

    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("[serial]\nbaudrate = 115200\n")
        test_path = Path(f.name)

    try:
        # Scenario 1: correct permissions — should succeed
        os.chmod(test_path, 0o600)
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            cm = ConfigManager()
            assert cm.config.baudrate == 115200

        # Scenario 2: incorrect permissions — reload() should raise 1008
        os.chmod(test_path, 0o644)
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            with pytest.raises(PermissionError) as exc:
                cm2 = ConfigManager()
                cm2.reload()
            assert "1008" in str(exc.value)

    finally:
        os.unlink(test_path)


def test_scenario_windows_skip_permission():
    """Scenario: Windows skips permission checks.

    Specification:
    - Decision 2: permission checks are only performed on Unix systems.
    """
    from uart_mcp.config import ConfigManager

    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("[serial]\nbaudrate = 115200\n")
        test_path = Path(f.name)

    try:
        os.chmod(test_path, 0o644)  # incorrect permissions

        # Windows should skip the permission check entirely
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Windows"):
            ConfigManager()  # noqa: F841 — should not raise

    finally:
        os.unlink(test_path)


if __name__ == "__main__":
    print("Running scenario tests: blacklist permission 600")
    print("=" * 60)
    test_scenario_blacklist_permission_600()
    print()
    test_scenario_config_permission_600()
    print()
    test_scenario_windows_skip_permission()
    print("=" * 60)
    print("\nAll scenario tests passed!")
