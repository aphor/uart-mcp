"""Tests for the configuration management module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import (
    BlacklistManager,
    ConfigManager,
    UartConfig,
    get_blacklist_manager,
    get_blacklist_path,
    get_config_dir,
    get_config_manager,
    get_config_path,
)


class TestUartConfig:
    """Tests for the UartConfig dataclass."""

    def test_default_values(self):
        """Test that default config values match the specification."""
        config = UartConfig()
        assert config.baudrate == 115200
        assert config.bytesize == 8
        assert config.parity == "N"
        assert config.stopbits == 1.0
        assert config.read_timeout == 1000
        assert config.write_timeout == 1000
        assert config.xonxoff is False
        assert config.rtscts is False
        assert config.dsrdtr is False
        assert config.auto_reconnect is True
        assert config.reconnect_interval == 5000
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = UartConfig(
            baudrate=115200,
            bytesize=7,
            parity="E",
            stopbits=2.0,
            read_timeout=2000,
            write_timeout=3000,
            xonxoff=True,
            auto_reconnect=False,
            log_level="DEBUG",
        )
        assert config.baudrate == 115200
        assert config.bytesize == 7
        assert config.parity == "E"
        assert config.stopbits == 2.0
        assert config.xonxoff is True
        assert config.auto_reconnect is False
        assert config.log_level == "DEBUG"


class TestConfigPaths:
    """Tests for config path generation."""

    def test_config_dir_linux(self):
        """Test the Linux config directory."""
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.home", return_value=Path("/home/user")):
                config_dir = get_config_dir()
                assert str(config_dir) == "/home/user/.uart-mcp"

    def test_config_dir_windows(self):
        """Test the Windows config directory."""
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
                config_dir = get_config_dir()
                assert str(config_dir).replace("\\", "/") == "C:/Users/user/AppData/Roaming/.uart-mcp"

    def test_config_path(self):
        """Test the config file path."""
        config_path = get_config_path()
        assert config_path.name == "config.toml"
        assert "uart-mcp" in str(config_path)

    def test_blacklist_path(self):
        """Test the blacklist file path."""
        blacklist_path = get_blacklist_path()
        assert blacklist_path.name == "blacklist.conf"
        assert "uart-mcp" in str(blacklist_path)


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_load_default_config(self):
        """Test loading the default config when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("uart_mcp.config.get_config_path", return_value=Path(tmpdir) / "nonexistent.toml"):
                cm = ConfigManager()
                config = cm.config
                assert config.baudrate == 115200  # uses default

    def test_load_config_from_file(self):
        """Test loading config from a file."""
        config_content = """
[serial]
baudrate = 115200
bytesize = 7

[timeout]
read_timeout = 2000

[reconnect]
auto_reconnect = false
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200
                assert cm.config.bytesize == 7
                assert cm.config.read_timeout == 2000
                assert cm.config.auto_reconnect is False

    def test_permission_check_unix(self):
        """Test Unix permission enforcement."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            # Set incorrect permissions
            os.chmod(test_path, 0o644)

            with patch("platform.system", return_value="Linux"):
                cm = ConfigManager()
                with pytest.raises(PermissionError) as exc:
                    cm._check_permission(test_path)
                assert "1008" in str(exc.value)
        finally:
            os.unlink(test_path)

    def test_permission_check_windows_skipped(self):
        """Test that permission checks are skipped on Windows."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            os.chmod(test_path, 0o644)  # incorrect permissions

            with patch("platform.system", return_value="Windows"):
                cm = ConfigManager()
                cm._check_permission(test_path)  # should not raise
        finally:
            os.unlink(test_path)

    def test_invalid_toml_handling(self):
        """Test handling of invalid TOML."""
        config_content = "invalid toml [[[["
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                # Should catch the error and fall back to defaults
                cm = ConfigManager()
                assert cm.config.baudrate == 115200  # uses default

    def test_reload_config(self):
        """Test hot-reloading the config."""
        config_content_v1 = """
[serial]
baudrate = 9600
"""
        config_content_v2 = """
[serial]
baudrate = 57600
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content_v1)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 9600

                # Update the file
                config_path.write_text(config_content_v2)
                os.chmod(config_path, 0o600)

                # Hot reload
                cm.reload()
                assert cm.config.baudrate == 57600

    def test_reload_preserves_old_on_error(self):
        """Test that hot-reload retains the old config on failure."""
        config_content = """
[serial]
baudrate = 115200
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200

                # Corrupt the file
                config_path.write_text("invalid [[[[")
                os.chmod(config_path, 0o600)

                # Reload should fail but retain the previous config
                with pytest.raises(ValueError):
                    cm.reload()
                assert cm.config.baudrate == 115200

    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns a singleton."""
        cm1 = get_config_manager()
        cm2 = get_config_manager()
        assert cm1 is cm2


class TestBlacklistManager:
    """Tests for the BlacklistManager class."""

    def test_no_blacklist_file(self):
        """Test with no blacklist file present."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("uart_mcp.config.get_blacklist_path", return_value=Path(tmpdir) / "nonexistent.conf"):
            bm = BlacklistManager()
            assert len(bm._patterns) == 0
            assert len(bm._exact_matches) == 0
            assert not bm.is_blacklisted("/dev/ttyUSB0")

    def test_exact_matching(self):
        """Test exact port matching."""
        content = "/dev/ttyUSB0\nCOM1\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("/dev/ttyUSB1") is False
                assert bm.is_blacklisted("COM2") is False

    def test_regex_matching(self):
        """Test regex pattern matching."""
        content = "COM[0-9]+\n/dev/ttyS[2-9]\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("COM55") is True
                assert bm.is_blacklisted("COMA") is False
                assert bm.is_blacklisted("/dev/ttyS2") is True
                assert bm.is_blacklisted("/dev/ttyS1") is False
                # [2-9] is a single-character class, so /dev/ttyS10 doesn't match
                assert bm.is_blacklisted("/dev/ttyS10") is False

    def test_comments_and_empty_lines(self):
        """Test that comments and blank lines are ignored."""
        content = """
# comment line
/dev/ttyUSB0

# another comment
COM[0-9]+

"""
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert len(bm._patterns) == 1
                assert len(bm._exact_matches) == 1

    def test_invalid_regex_skipped(self):
        """Test that invalid regex patterns are skipped."""
        content = "/dev/ttyUSB0\n[invalid(\n/dev/ttyACM0\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                # 2 exact matches, 0 patterns (invalid one skipped)
                assert len(bm._exact_matches) == 2
                assert len(bm._patterns) == 0

    def test_permission_check_unix(self):
        """Test permission enforcement for the blacklist file."""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("/dev/ttyUSB0\n")
            test_path = Path(f.name)

        try:
            os.chmod(test_path, 0o644)  # incorrect permissions

            with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
                 patch("platform.system", return_value="Linux"):
                with pytest.raises(PermissionError) as exc:
                    BlacklistManager()
                assert "1008" in str(exc.value)
        finally:
            os.unlink(test_path)

    def test_reload_blacklist(self):
        """Test hot-reloading the blacklist."""
        content_v1 = "/dev/ttyUSB0\n"
        content_v2 = "/dev/ttyUSB1\nCOM[0-9]+\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content_v1)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                assert bm.is_blacklisted("COM1") is False

                # Update the file
                blacklist_path.write_text(content_v2)
                os.chmod(blacklist_path, 0o600)

                # Hot reload
                bm.reload()
                assert bm.is_blacklisted("/dev/ttyUSB1") is True
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("/dev/ttyUSB0") is False  # removed

    def test_reload_failure_rollback(self):
        """Test that a failed hot-reload rolls back to the previous state."""
        content_v1 = "/dev/ttyUSB0\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content_v1)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
                 patch("platform.system", return_value="Linux"):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                original_count = len(bm._patterns) + len(bm._exact_matches)

                # Change permissions to force a load failure
                os.chmod(blacklist_path, 0o644)

                # Reload should fail and raise
                with pytest.raises(PermissionError):
                    bm.reload()

                # Rules should be unchanged (rolled back)
                assert len(bm._patterns) + len(bm._exact_matches) == original_count
                assert bm.is_blacklisted("/dev/ttyUSB0") is True


class TestIntegration:
    """Integration tests."""

    def test_singletons(self):
        """Test that all managers are singletons."""
        cm1 = get_config_manager()
        cm2 = get_config_manager()
        assert cm1 is cm2

        bm1 = get_blacklist_manager()
        bm2 = get_blacklist_manager()
        assert bm1 is bm2

    def test_config_and_blacklist_coexist(self):
        """Test that config and blacklist managers work side by side."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            blacklist_path = Path(tmpdir) / "blacklist.conf"

            config_path.write_text("[serial]\nbaudrate = 115200\n")
            blacklist_path.write_text("/dev/ttyUSB0\n")

            os.chmod(config_path, 0o600)
            os.chmod(blacklist_path, 0o600)

            # Use fresh instances, not singletons
            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
                 patch("platform.system", return_value="Linux"):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True


# Reset singletons for test isolation
def reset_singletons():
    """Reset singletons (for testing)."""
    global _config_manager, _blacklist_manager
    _config_manager = None
    _blacklist_manager = None


# Module-level variable reset
_blacklist_manager = None
_config_manager = None
