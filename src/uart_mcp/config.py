"""Configuration management module.

Manages the serial port blacklist and global configuration.
"""

import logging
import os
import platform
import re
import threading
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported baud rates and data bits (kept in sync with types.py for consistency)
SUPPORTED_BAUDRATES: tuple[int, ...] = (
    300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600,
    115200, 230400, 460800, 921600,
)
SUPPORTED_BYTESIZES: tuple[int, ...] = (5, 6, 7, 8)
SUPPORTED_PARITIES: tuple[str, ...] = ("N", "E", "O", "M", "S")
SUPPORTED_STOPBITS: tuple[float, ...] = (1.0, 1.5, 2.0)
SUPPORTED_LOG_LEVELS: tuple[str, ...] = (
    "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
)


@dataclass
class UartConfig:
    """Global configuration.

    Attributes:
        baudrate: Baud rate.
        bytesize: Data bits.
        parity: Parity bit.
        stopbits: Stop bits.
        read_timeout: Read timeout (milliseconds).
        write_timeout: Write timeout (milliseconds).
        xonxoff: Software flow control.
        rtscts: Hardware flow control.
        dsrdtr: DSR/DTR flow control.
        auto_reconnect: Auto-reconnect toggle.
        reconnect_interval: Reconnect interval (milliseconds).
        log_level: Log level.
    """

    # Serial port defaults
    baudrate: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    # Timeout settings (milliseconds)
    read_timeout: int = 1000
    write_timeout: int = 1000
    # Flow control
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False
    # Auto-reconnect
    auto_reconnect: bool = True
    reconnect_interval: int = 5000
    # Log level
    log_level: str = "INFO"


def get_config_dir() -> Path:
    """Return the configuration directory.

    Returns the directory path appropriate for the operating system.

    Returns:
        Configuration directory path.
    """
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / ".uart-mcp"
    else:  # Linux/macOS
        return Path.home() / ".uart-mcp"


def get_config_path() -> Path:
    """Return the configuration file path.

    Returns:
        Configuration file path.
    """
    return get_config_dir() / "config.toml"


def get_blacklist_path() -> Path:
    """Return the blacklist configuration file path.

    Returns:
        Blacklist file path.
    """
    return get_config_dir() / "blacklist.conf"


class ConfigManager:
    """Configuration manager.

    Loads, parses, and manages the global configuration file.

    Attributes:
        _config: The current configuration instance.
        _lock: Lock guarding concurrent access during hot reload.
    """

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._config: UartConfig = UartConfig()
        self._lock = threading.Lock()
        self._load_config()

    def _check_permission(self, path: Path) -> None:
        """Check file permissions (Unix systems only).

        Args:
            path: File path.

        Raises:
            PermissionError: Permissions do not match (error code 1008).
        """
        import stat

        # Only perform permission checks on Unix systems
        if platform.system() in ("Linux", "Darwin"):
            mode = path.stat().st_mode
            file_perm = stat.S_IMODE(mode)
            # 600 = rw------- (owner read/write only)
            if file_perm != 0o600:
                raise PermissionError(
                    f"Configuration file permissions must be 600 (rw-------), "
                    f"currently {oct(file_perm)}, error code: 1008"
                )

    def _load_config_from_file(self, config_path: Path) -> UartConfig:
        """Load configuration from a file.

        Args:
            config_path: Configuration file path.

        Returns:
            Parsed configuration object.

        Raises:
            PermissionError: Permission check failed (error code 1008).
            ValueError: Parsing failed or a value is out of range (error code 1005).
        """
        # Permission check
        if config_path.exists():
            self._check_permission(config_path)

        # Read and parse TOML
        try:
            with config_path.open("rb") as f:
                config_dict: dict[str, Any] = tomllib.load(f)
        except FileNotFoundError:
            logger.info("Configuration file not found; using defaults: %s", config_path)
            return UartConfig()
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"TOML parse failed, error code: 1005, reason: {e}") from e
        except Exception as e:
            raise ValueError(
                f"Failed to read configuration file, error code: 1005, reason: {e}"
            ) from e

        # Build the config object (missing fields fall back to defaults)
        config = self._build_config_from_dict(config_dict)

        # Value range validation (warn rather than block loading)
        self._validate_config_ranges(config)

        return config

    def _build_config_from_dict(self, config_dict: dict[str, Any]) -> UartConfig:
        """Build a configuration object from a dict (with type validation).

        Args:
            config_dict: Configuration dictionary.

        Returns:
            Configuration object.

        Raises:
            ValueError: Type is wrong or a value is invalid.
        """
        config = UartConfig()

        # Serial port config
        serial = config_dict.get("serial", {})
        if "baudrate" in serial:
            raw = serial["baudrate"]
            if not isinstance(raw, int):
                raise ValueError(f"baudrate must be an integer, got {type(raw).__name__}")
            config.baudrate = raw
        if "bytesize" in serial:
            raw = serial["bytesize"]
            if not isinstance(raw, int):
                raise ValueError(f"bytesize must be an integer, got {type(raw).__name__}")
            config.bytesize = raw
        if "parity" in serial:
            raw = serial["parity"]
            if not isinstance(raw, str):
                raise ValueError(f"parity must be a string, got {type(raw).__name__}")
            config.parity = raw
        if "stopbits" in serial:
            raw = serial["stopbits"]
            if not isinstance(raw, (int, float)):
                raise ValueError(f"stopbits must be a number, got {type(raw).__name__}")
            config.stopbits = float(raw)

        # Timeout config
        timeout = config_dict.get("timeout", {})
        if "read_timeout" in timeout:
            raw = timeout["read_timeout"]
            if not isinstance(raw, int):
                raise ValueError(
                    f"read_timeout must be an integer, got {type(raw).__name__}"
                )
            config.read_timeout = raw
        if "write_timeout" in timeout:
            raw = timeout["write_timeout"]
            if not isinstance(raw, int):
                raise ValueError(
                    f"write_timeout must be an integer, got {type(raw).__name__}"
                )
            config.write_timeout = raw

        # Flow control config
        flow_control = config_dict.get("flow_control", {})
        if "xonxoff" in flow_control:
            raw = flow_control["xonxoff"]
            if not isinstance(raw, bool):
                raise ValueError(f"xonxoff must be a boolean, got {type(raw).__name__}")
            config.xonxoff = raw
        if "rtscts" in flow_control:
            raw = flow_control["rtscts"]
            if not isinstance(raw, bool):
                raise ValueError(f"rtscts must be a boolean, got {type(raw).__name__}")
            config.rtscts = raw
        if "dsrdtr" in flow_control:
            raw = flow_control["dsrdtr"]
            if not isinstance(raw, bool):
                raise ValueError(f"dsrdtr must be a boolean, got {type(raw).__name__}")
            config.dsrdtr = raw

        # Reconnect config
        reconnect = config_dict.get("reconnect", {})
        if "auto_reconnect" in reconnect:
            raw = reconnect["auto_reconnect"]
            if not isinstance(raw, bool):
                raise ValueError(
                    f"auto_reconnect must be a boolean, got {type(raw).__name__}"
                )
            config.auto_reconnect = raw
        if "reconnect_interval" in reconnect:
            raw = reconnect["reconnect_interval"]
            if not isinstance(raw, int):
                raise ValueError(
                    f"reconnect_interval must be an integer, got {type(raw).__name__}"
                )
            config.reconnect_interval = raw

        # Logging config
        logging_cfg = config_dict.get("logging", {})
        if "log_level" in logging_cfg:
            raw = logging_cfg["log_level"]
            if not isinstance(raw, str):
                raise ValueError(
                    f"log_level must be a string, got {type(raw).__name__}"
                )
            config.log_level = raw

        return config

    def _validate_config_ranges(self, config: UartConfig) -> None:
        """Validate configuration value ranges (warning-style validation).

        Args:
            config: Configuration object to validate.
        """
        # Validate baud rate
        if config.baudrate not in SUPPORTED_BAUDRATES:
            logger.warning(
                "Baud rate %d is not in the standard list; "
                "communication stability may be affected. Supported values: %s",
                config.baudrate, SUPPORTED_BAUDRATES
            )

        # Validate data bits
        if config.bytesize not in SUPPORTED_BYTESIZES:
            logger.warning(
                "Data bits %d is not in the standard list. Supported values: %s",
                config.bytesize, SUPPORTED_BYTESIZES
            )

        # Validate parity
        if config.parity not in SUPPORTED_PARITIES:
            logger.warning(
                "Parity '%s' is not in the standard list. Supported values: %s",
                config.parity, SUPPORTED_PARITIES
            )

        # Validate stop bits
        if config.stopbits not in SUPPORTED_STOPBITS:
            logger.warning(
                "Stop bits %s is not in the standard list. Supported values: %s",
                config.stopbits, SUPPORTED_STOPBITS
            )

        # Validate timeout range (recommended values)
        if config.read_timeout < 0 or config.read_timeout > 60000:
            logger.warning(
                "Read timeout %dms is outside the recommended range (0-60000ms); "
                "real-world behavior may be unstable",
                config.read_timeout
            )
        if config.write_timeout < 0 or config.write_timeout > 60000:
            logger.warning(
                "Write timeout %dms is outside the recommended range (0-60000ms); "
                "real-world behavior may be unstable",
                config.write_timeout
            )

        # Validate reconnect interval
        if config.reconnect_interval < 1000 or config.reconnect_interval > 300000:
            logger.warning(
                "Reconnect interval %dms is outside the recommended range "
                "(1000-300000ms); real-world behavior may be unstable",
                config.reconnect_interval
            )

        # Validate log level
        if config.log_level not in SUPPORTED_LOG_LEVELS:
            logger.warning(
                "Log level '%s' is not in the standard list. Supported values: %s",
                config.log_level, SUPPORTED_LOG_LEVELS
            )

    def _load_config(self) -> None:
        """Load the configuration file (internal use)."""
        config_path = get_config_path()
        try:
            new_config = self._load_config_from_file(config_path)
            self._config = new_config
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(
                "Configuration load failed: %s; keeping current configuration", e
            )

    def reload(self) -> None:
        """Reload the configuration.

        Called on manual trigger or background monitor trigger.
        The previous configuration is retained until the new one parses successfully.

        Raises:
            PermissionError: Permission check failed (error code 1008).
            ValueError: Parsing failed (error code 1005).
        """
        with self._lock:
            old_config = self._config
            config_path = get_config_path()
            try:
                new_config = self._load_config_from_file(config_path)
                self._config = new_config
                logger.info("Configuration hot-reload succeeded")
            except Exception as e:
                # Keep the old configuration on failure
                self._config = old_config
                logger.warning(
                    "Configuration hot-reload failed; keeping old configuration: %s", e
                )
                raise

    @property
    def config(self) -> UartConfig:
        """Return the current configuration.

        Returns:
            Current configuration object.
        """
        with self._lock:
            return self._config


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Return the configuration manager singleton.

    Returns:
        Configuration manager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


class BlacklistManager:
    """Blacklist manager.

    Manages the serial port blacklist with support for exact matches and
    regular-expression matches.

    Attributes:
        _patterns: Compiled regular expression patterns.
        _exact_matches: Exact-match serial port entries.
        _lock: Lock guarding concurrent access during hot reload.
    """

    def __init__(self) -> None:
        """Initialize the blacklist manager."""
        self._patterns: list[re.Pattern[str]] = []
        self._exact_matches: set[str] = set()
        self._lock = threading.Lock()
        self._load_blacklist()

    def _check_permission(self, path: Path) -> None:
        """Check blacklist file permissions (Unix systems only).

        Args:
            path: File path.

        Raises:
            PermissionError: Permissions do not match (error code 1008).
        """
        import stat

        # Only perform permission checks on Unix systems
        if platform.system() in ("Linux", "Darwin"):
            mode = path.stat().st_mode
            file_perm = stat.S_IMODE(mode)
            # 600 = rw------- (owner read/write only)
            if file_perm != 0o600:
                raise PermissionError(
                    f"Blacklist file permissions must be 600 (rw-------), "
                    f"currently {oct(file_perm)}, error code: 1008"
                )

    def _load_blacklist(self) -> None:
        """Load the blacklist from the configuration file."""
        blacklist_path = get_blacklist_path()
        if not blacklist_path.exists():
            logger.debug("Blacklist configuration file not found: %s", blacklist_path)
            return

        # Permission check
        try:
            self._check_permission(blacklist_path)
        except PermissionError as e:
            logger.error("Blacklist file permission check failed: %s", e)
            raise

        try:
            with blacklist_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip blank lines and comments
                    if not line or line.startswith("#"):
                        continue
                    self._add_entry(line)
            rule_count = len(self._patterns) + len(self._exact_matches)
            logger.info("Blacklist loaded, %d rules total", rule_count)
        except OSError as e:
            logger.error("Failed to read blacklist configuration file: %s", e)
            raise

    def _add_entry(self, entry: str) -> None:
        """Add a blacklist entry.

        If the entry contains regular expression meta-characters (such as square
        brackets) it is treated as a regex; otherwise it is treated as an exact match.

        Args:
            entry: Blacklist entry.
        """
        # Check whether the entry contains regex meta-characters
        if any(c in entry for c in r"[]{}()*+?|^$.\\"):
            try:
                pattern = re.compile(entry)
                self._patterns.append(pattern)
                logger.debug("Added regex blacklist rule: %s", entry)
            except re.error as e:
                logger.warning("Invalid regular expression '%s', skipped: %s", entry, e)
        else:
            self._exact_matches.add(entry)
            logger.debug("Added exact blacklist rule: %s", entry)

    def is_blacklisted(self, port: str) -> bool:
        """Check whether a serial port is blacklisted.

        Args:
            port: Serial port path.

        Returns:
            True if blacklisted, False otherwise.
        """
        # Exact match
        if port in self._exact_matches:
            return True

        # Regex match
        for pattern in self._patterns:
            if pattern.search(port):
                return True

        return False

    def reload(self) -> None:
        """Reload the blacklist configuration.

        Returns:
            None

        Raises:
            PermissionError: Permission check failed (error code 1008).
            OSError: File read failed.
        """
        with self._lock:
            old_patterns = self._patterns.copy()
            old_exact_matches = self._exact_matches.copy()

            self._patterns.clear()
            self._exact_matches.clear()

            try:
                self._load_blacklist()
                logger.info("Blacklist hot-reload succeeded")
            except Exception as e:
                # Restore old rules on load failure
                self._patterns = old_patterns
                self._exact_matches = old_exact_matches
                logger.warning(
                    "Blacklist hot-reload failed; keeping old rules: %s", e
                )
                raise


# Global blacklist manager instance
_blacklist_manager: BlacklistManager | None = None


def get_blacklist_manager() -> BlacklistManager:
    """Return the blacklist manager singleton.

    Returns:
        Blacklist manager instance.
    """
    global _blacklist_manager
    if _blacklist_manager is None:
        _blacklist_manager = BlacklistManager()
    return _blacklist_manager
