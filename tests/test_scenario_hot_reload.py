"""Scenario tests: hot-reload behaviour (specification requirements).

Per the specification:
- When the config reload logic is called, the config file is re-read and
  permission / parse checks are run.
- On success the in-memory state is updated with the new config.
- On failure the old config is retained and the corresponding error is returned.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import BlacklistManager, ConfigManager, UartConfig


def test_scenario_config_reload_success():
    """Scenario: config hot-reload succeeds.

    Specification:
    - WHEN the config reload logic is called
    - THEN the config file is re-read and permission / parse checks run
    - AND on success the in-memory state is updated with the new config
    """
    config_v1 = """
[serial]
baudrate = 9600
bytesize = 8

[timeout]
read_timeout = 1000
"""

    config_v2 = """
[serial]
baudrate = 115200
bytesize = 7

[timeout]
read_timeout = 2000
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_v1)
        os.chmod(config_path, 0o600)

        # Use a fresh manager instance per test to avoid singleton interference
        with patch("uart_mcp.config.get_config_path", return_value=config_path):
            cm = ConfigManager()
            cm._config = UartConfig()  # set initial state manually
            cm._load_config()  # load config_v1

            cm2 = ConfigManager()
            assert cm2.config.baudrate == 9600
            assert cm2.config.bytesize == 8
            assert cm2.config.read_timeout == 1000

            # Update the file (permissions still correct)
            config_path.write_text(config_v2)
            os.chmod(config_path, 0o600)

            # Hot reload
            cm2.reload()

            # Verify the new config is active
            assert cm2.config.baudrate == 115200
            assert cm2.config.bytesize == 7
            assert cm2.config.read_timeout == 2000


def test_scenario_config_reload_permission_error():
    """Scenario: config hot-reload fails due to a permission error; old config retained.

    Specification:
    - On failure the old config is retained and the corresponding error returned.
    """
    config_content = """
[serial]
baudrate = 9600
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_content)
        os.chmod(config_path, 0o600)

        with patch("uart_mcp.config.get_config_path", return_value=config_path), \
             patch("platform.system", return_value="Linux"):
            cm = ConfigManager()
            original_baudrate = cm.config.baudrate

            # Change to incorrect permissions
            os.chmod(config_path, 0o644)

            # Hot reload should fail
            with pytest.raises(PermissionError) as exc:
                cm.reload()
            assert "1008" in str(exc.value)

            # Old config must be retained
            assert cm.config.baudrate == original_baudrate


def test_scenario_config_reload_toml_error():
    """Scenario: config hot-reload fails due to a TOML parse error; old config retained.

    Specification:
    - Config file exists but TOML parsing fails, or field values / types are invalid
    - Returns error code 1005
    - Retains the current valid config
    """
    config_v1 = """
[serial]
baudrate = 9600
"""

    invalid_toml = "[[invalid "  # incomplete TOML

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_v1)
        os.chmod(config_path, 0o600)

        with patch("uart_mcp.config.get_config_path", return_value=config_path):
            cm = ConfigManager()
            original_baudrate = cm.config.baudrate

            # Replace with invalid TOML
            config_path.write_text(invalid_toml)
            os.chmod(config_path, 0o600)

            # Hot reload should fail
            with pytest.raises(ValueError) as exc:
                cm.reload()
            assert "1005" in str(exc.value)

            # Old config must be retained
            assert cm.config.baudrate == original_baudrate


def test_scenario_blacklist_reload_success():
    """Scenario: blacklist hot-reload succeeds.

    Specification:
    - WHEN the blacklist reload logic is called
    - THEN the cached rules are cleared and the file is re-parsed
    - AND new rules take effect immediately for subsequent list_ports / open_port calls
    """
    rules_v1 = "/dev/ttyUSB0\n"
    rules_v2 = "/dev/ttyUSB1\nCOM[0-9]+\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        blacklist_path = Path(tmpdir) / "blacklist.conf"
        blacklist_path.write_text(rules_v1)
        os.chmod(blacklist_path, 0o600)

        with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            assert bm.is_blacklisted("/dev/ttyUSB1") is False

            # Update rules
            blacklist_path.write_text(rules_v2)
            os.chmod(blacklist_path, 0o600)

            # Hot reload
            bm.reload()

            # New rules take effect immediately
            assert bm.is_blacklisted("/dev/ttyUSB0") is False
            assert bm.is_blacklisted("/dev/ttyUSB1") is True
            assert bm.is_blacklisted("COM1") is True


def test_scenario_blacklist_reload_error_rollback():
    """Scenario: blacklist hot-reload fails; old rules retained.

    Specification:
    - On parse failure the old rules are retained and the corresponding error returned.

    When blacklist reload fails, rules are rolled back and then the exception is raised.
    """
    rules_v1 = "/dev/ttyUSB0\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        blacklist_path = Path(tmpdir) / "blacklist.conf"
        blacklist_path.write_text(rules_v1)
        os.chmod(blacklist_path, 0o600)

        with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
             patch("platform.system", return_value="Linux"):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            original_count = len(bm._patterns) + len(bm._exact_matches)

            # Corrupt permissions to force a load failure
            os.chmod(blacklist_path, 0o644)

            # reload should roll back rules then raise
            with pytest.raises(PermissionError):
                bm.reload()

            # Verify rollback occurred
            assert len(bm._patterns) + len(bm._exact_matches) == original_count
            assert bm.is_blacklisted("/dev/ttyUSB0") is True


if __name__ == "__main__":
    print("Running scenario tests: hot-reload")
    print("=" * 60)
    test_scenario_config_reload_success()
    test_scenario_config_reload_permission_error()
    test_scenario_config_reload_toml_error()
    test_scenario_blacklist_reload_success()
    test_scenario_blacklist_reload_error_rollback()
    print("=" * 60)
    print("\nAll hot-reload scenario tests passed!")
