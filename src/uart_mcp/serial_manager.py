"""Serial port manager module.

Provides the core functionality for enumerating, opening, closing, and
configuring serial ports.
"""

import logging
import threading
import time
from typing import Any

import serial
import serial.tools.list_ports
from serial import SerialException

from .config import get_blacklist_manager, get_config_manager
from .errors import (
    InvalidParamError,
    PermissionDeniedError,
    PortBlacklistedError,
    PortBusyError,
    PortClosedError,
    PortNotFoundError,
    PortOpenFailedError,
    WriteFailedError,
)
from .types import (
    SUPPORTED_BAUDRATES,
    SUPPORTED_BYTESIZES,
    FlowControl,
    Parity,
    PortInfo,
    PortStatus,
    SerialConfig,
    StopBits,
)

logger = logging.getLogger(__name__)

# Reconnect-check interval (seconds)
RECONNECT_CHECK_INTERVAL = 2.0
# Reconnect-retry interval (seconds)
RECONNECT_RETRY_INTERVAL = 3.0


class ManagedPort:
    """A managed serial port connection.

    Wraps pyserial's Serial object and adds configuration and state tracking.

    Attributes:
        port: Serial port path.
        serial: pyserial Serial object.
        config: Serial port configuration.
        reconnecting: Whether a reconnect is in progress.
        auto_reconnect: Whether auto-reconnect is enabled.
    """

    def __init__(
        self,
        port: str,
        serial_obj: serial.Serial,
        config: SerialConfig,
        auto_reconnect: bool = True,
    ) -> None:
        self.port = port
        self.serial = serial_obj
        self.config = config
        self.reconnecting = False
        self.auto_reconnect = auto_reconnect
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check the physical connection state."""
        try:
            # Try reading DSR state to probe the connection.
            # If the port has been disconnected, this raises an exception.
            if self.serial.is_open:
                # Some ports may not support DSR, so we probe via in_waiting
                _ = self.serial.in_waiting
                return True
        except (SerialException, OSError):
            pass
        return False


class SerialManager:
    """Serial port manager.

    Provides enumeration, opening, closing, and configuration of serial
    devices. Supports concurrent multi-port connections, configuration
    hot-update, and auto-reconnect.

    Attributes:
        _ports: Dict of open ports keyed by port path.
        _lock: Thread lock.
        _reconnect_thread: Reconnect-check thread.
        _running: Whether the manager is running.
    """

    def __init__(self, enable_auto_reconnect: bool = True) -> None:
        """Initialize the serial port manager.

        Args:
            enable_auto_reconnect: Whether to enable the auto-reconnect feature.
        """
        self._ports: dict[str, ManagedPort] = {}
        self._lock = threading.RLock()
        self._running = True
        self._enable_auto_reconnect = enable_auto_reconnect
        self._reconnect_thread: threading.Thread | None = None

        if enable_auto_reconnect:
            self._start_reconnect_thread()

    def _start_reconnect_thread(self) -> None:
        """Start the reconnect-check thread."""
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True, name="serial-reconnect"
        )
        self._reconnect_thread.start()
        logger.debug("Reconnect-check thread started")

    def _reconnect_loop(self) -> None:
        """Reconnect-check loop."""
        while self._running:
            try:
                self._check_and_reconnect()
            except Exception as e:
                logger.error("Reconnect check raised an exception: %s", e)
            time.sleep(RECONNECT_CHECK_INTERVAL)

    def _check_and_reconnect(self) -> None:
        """Check for disconnected ports and reconnect them."""
        with self._lock:
            ports_to_reconnect: list[tuple[str, SerialConfig]] = []
            for port_path, managed in list(self._ports.items()):
                if not managed.auto_reconnect:
                    continue
                if not managed.is_connected and not managed.reconnecting:
                    logger.info("Detected port disconnection: %s", port_path)
                    managed.reconnecting = True
                    ports_to_reconnect.append((port_path, managed.config))

        # Perform the reconnect outside the lock
        for port_path, config in ports_to_reconnect:
            self._try_reconnect(port_path, config)

    def _try_reconnect(self, port: str, config: SerialConfig) -> None:
        """Attempt to reconnect a serial port.

        Args:
            port: Serial port path.
            config: Serial port configuration.
        """
        logger.info("Attempting to reconnect serial port: %s", port)
        try:
            serial_obj = self._create_serial(port, config)
            with self._lock:
                if port in self._ports:
                    old_managed = self._ports[port]
                    try:
                        old_managed.serial.close()
                    except Exception:
                        pass
                    # Preserve the original auto_reconnect setting
                    self._ports[port] = ManagedPort(
                        port,
                        serial_obj,
                        config,
                        auto_reconnect=old_managed.auto_reconnect,
                    )
                    logger.info("Serial port reconnected successfully: %s", port)
                else:
                    # The port was closed during reconnect; release the new resource
                    serial_obj.close()
                    logger.info(
                        "Serial port was closed during reconnect; "
                        "newly created resource released: %s",
                        port,
                    )
        except Exception as e:
            logger.warning("Serial port reconnect failed: %s - %s", port, e)
            with self._lock:
                if port in self._ports:
                    self._ports[port].reconnecting = False

    def _create_serial(self, port: str, config: SerialConfig) -> serial.Serial:
        """Create a pyserial Serial object.

        Args:
            port: Serial port path.
            config: Serial port configuration.

        Returns:
            Configured Serial object.

        Raises:
            PortNotFoundError: Serial port does not exist.
            PortBusyError: Serial port is in use.
            PortOpenFailedError: Failed to open the port.
        """
        # Translate configuration
        parity_map = {
            Parity.NONE: serial.PARITY_NONE,
            Parity.EVEN: serial.PARITY_EVEN,
            Parity.ODD: serial.PARITY_ODD,
            Parity.MARK: serial.PARITY_MARK,
            Parity.SPACE: serial.PARITY_SPACE,
        }

        stopbits_map = {
            StopBits.ONE: serial.STOPBITS_ONE,
            StopBits.ONE_POINT_FIVE: serial.STOPBITS_ONE_POINT_FIVE,
            StopBits.TWO: serial.STOPBITS_TWO,
        }

        try:
            serial_obj = serial.Serial(
                port=port,
                baudrate=config.baudrate,
                bytesize=config.bytesize,
                parity=parity_map[config.parity],
                stopbits=stopbits_map[config.stopbits],
                timeout=config.read_timeout_ms / 1000.0,
                write_timeout=config.write_timeout_ms / 1000.0,
                xonxoff=config.flow_control == FlowControl.SOFTWARE,
                rtscts=config.flow_control == FlowControl.HARDWARE,
            )
            return serial_obj
        except serial.SerialException as e:
            error_msg = str(e).lower()
            if "no such file" in error_msg or "not found" in error_msg:
                raise PortNotFoundError(port) from e
            if "permission" in error_msg or "access" in error_msg:
                raise PermissionDeniedError(port) from e
            if "busy" in error_msg or "in use" in error_msg:
                raise PortBusyError(port) from e
            raise PortOpenFailedError(port, str(e)) from e

    def list_ports(self) -> list[PortInfo]:
        """List all available serial ports.

        Returns all serial ports available on the system, filtered by the
        blacklist.

        Returns:
            List of serial port info.
        """
        blacklist = get_blacklist_manager()
        ports: list[PortInfo] = []

        for port_info in serial.tools.list_ports.comports():
            if blacklist.is_blacklisted(port_info.device):
                logger.debug(
                    "Serial port is blacklisted, filtered out: %s", port_info.device
                )
                continue
            ports.append(
                PortInfo(
                    port=port_info.device,
                    description=port_info.description or "",
                    hwid=port_info.hwid or "",
                )
            )

        return ports

    def open_port(
        self,
        port: str,
        baudrate: int | None = None,
        bytesize: int | None = None,
        parity: str | None = None,
        stopbits: float | None = None,
        flow_control: str | None = None,
        read_timeout_ms: int | None = None,
        write_timeout_ms: int | None = None,
        auto_reconnect: bool | None = None,
    ) -> PortStatus:
        """Open a serial port.

        Args:
            port: Serial port path.
            baudrate: Baud rate (falls back to config default if None).
            bytesize: Data bits (falls back to config default if None).
            parity: Parity bit (falls back to config default if None).
            stopbits: Stop bits (falls back to config default if None).
            flow_control: Flow control (falls back to config default if None).
            read_timeout_ms: Read timeout in ms (falls back to config default if None).
            write_timeout_ms: Write timeout in ms (falls back to config default if None).
            auto_reconnect: Enable auto-reconnect (falls back to config default if None).

        Returns:
            Serial port status.

        Raises:
            PortBlacklistedError: Port is blacklisted.
            PortNotFoundError: Port does not exist.
            PortBusyError: Port is in use.
            InvalidParamError: Parameter is invalid.
        """
        # Check blacklist
        blacklist = get_blacklist_manager()
        if blacklist.is_blacklisted(port):
            raise PortBlacklistedError(port)

        # Use global config as the default source
        global_config = get_config_manager().config

        # Prefer explicit arguments over config defaults
        final_baudrate = baudrate if baudrate is not None else global_config.baudrate
        final_bytesize = bytesize if bytesize is not None else global_config.bytesize
        final_parity = parity if parity is not None else global_config.parity
        final_stopbits = stopbits if stopbits is not None else global_config.stopbits
        # Flow control: explicit argument wins
        if flow_control is None:
            final_flow_control = (
                "software" if global_config.xonxoff else
                "hardware" if global_config.rtscts else
                "none"
            )
        else:
            final_flow_control = flow_control
        cc = global_config
        rt = read_timeout_ms
        wt = write_timeout_ms
        ar = auto_reconnect
        final_read_timeout = cc.read_timeout if rt is None else rt
        final_write_timeout = cc.write_timeout if wt is None else wt
        final_auto_reconnect = cc.auto_reconnect if ar is None else ar

        # Validate parameters
        config = self._validate_and_create_config(
            final_baudrate,
            final_bytesize,
            final_parity,
            final_stopbits,
            final_flow_control,
            final_read_timeout,
            final_write_timeout,
        )

        with self._lock:
            # Check if already open (idempotent)
            if port in self._ports:
                managed = self._ports[port]
                logger.info(
                    "Serial port already open; returning current status: %s", port
                )
                return PortStatus(
                    port=port,
                    is_open=True,
                    config=managed.config,
                    connected=managed.is_connected,
                    reconnecting=managed.reconnecting,
                )

            # Open the port
            serial_obj = self._create_serial(port, config)
            managed = ManagedPort(port, serial_obj, config, final_auto_reconnect)
            self._ports[port] = managed
            logger.info("Serial port opened successfully: %s", port)

            return PortStatus(
                port=port,
                is_open=True,
                config=config,
                connected=managed.is_connected,
                reconnecting=False,
            )

    def _validate_and_create_config(
        self,
        baudrate: int,
        bytesize: int,
        parity: str,
        stopbits: float,
        flow_control: str,
        read_timeout_ms: int,
        write_timeout_ms: int,
    ) -> SerialConfig:
        """Validate parameters and build a configuration object.

        Raises:
            InvalidParamError: Parameter is invalid.
        """
        # Validate baud rate
        if baudrate not in SUPPORTED_BAUDRATES:
            raise InvalidParamError(
                "baudrate", baudrate, f"supported values: {SUPPORTED_BAUDRATES}"
            )

        # Validate data bits
        if bytesize not in SUPPORTED_BYTESIZES:
            raise InvalidParamError(
                "bytesize", bytesize, f"supported values: {SUPPORTED_BYTESIZES}"
            )

        # Validate parity
        try:
            parity_enum = Parity(parity)
        except ValueError:
            raise InvalidParamError(
                "parity", parity, f"supported values: {[p.value for p in Parity]}"
            )

        # Validate stop bits
        try:
            stopbits_enum = StopBits(stopbits)
        except ValueError:
            raise InvalidParamError(
                "stopbits", stopbits, f"supported values: {[s.value for s in StopBits]}"
            )

        # Validate flow control
        try:
            flow_enum = FlowControl(flow_control)
        except ValueError:
            valid_values = [f.value for f in FlowControl]
            raise InvalidParamError(
                "flow_control", flow_control, f"supported values: {valid_values}"
            )

        # Validate timeouts
        if read_timeout_ms < 0 or read_timeout_ms > 60000:
            raise InvalidParamError(
                "read_timeout_ms", read_timeout_ms, "range: 0-60000"
            )
        if write_timeout_ms < 0 or write_timeout_ms > 60000:
            raise InvalidParamError(
                "write_timeout_ms", write_timeout_ms, "range: 0-60000"
            )

        return SerialConfig(
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity_enum,
            stopbits=stopbits_enum,
            flow_control=flow_enum,
            read_timeout_ms=read_timeout_ms,
            write_timeout_ms=write_timeout_ms,
        )

    def close_port(self, port: str) -> dict[str, Any]:
        """Close a serial port.

        Args:
            port: Serial port path.

        Returns:
            Operation result.

        Raises:
            PortClosedError: Serial port is not open.
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports.pop(port)
            try:
                managed.serial.close()
            except Exception as e:
                logger.warning(
                    "Exception raised while closing serial port: %s - %s", port, e
                )

            logger.info("Serial port closed successfully: %s", port)
            return {"success": True, "port": port}

    def set_config(
        self,
        port: str,
        baudrate: int | None = None,
        bytesize: int | None = None,
        parity: str | None = None,
        stopbits: float | None = None,
        flow_control: str | None = None,
        read_timeout_ms: int | None = None,
        write_timeout_ms: int | None = None,
    ) -> PortStatus:
        """Update serial port configuration (hot update).

        Args:
            port: Serial port path.
            baudrate: Baud rate (optional).
            bytesize: Data bits (optional).
            parity: Parity bit (optional).
            stopbits: Stop bits (optional).
            flow_control: Flow control (optional).
            read_timeout_ms: Read timeout (optional).
            write_timeout_ms: Write timeout (optional).

        Returns:
            Updated serial port status.

        Raises:
            PortClosedError: Serial port is not open.
            InvalidParamError: Parameter is invalid.
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            current_config = managed.config

            # Build new config; unspecified params keep their current values
            cc = current_config  # shorthand
            new_baudrate = baudrate if baudrate is not None else cc.baudrate
            new_bytesize = bytesize if bytesize is not None else cc.bytesize
            new_parity = parity if parity is not None else cc.parity.value
            new_stopbits = stopbits if stopbits is not None else cc.stopbits.value
            new_flow = (
                flow_control if flow_control is not None else cc.flow_control.value
            )
            new_read_timeout = (
                read_timeout_ms if read_timeout_ms is not None else cc.read_timeout_ms
            )
            new_write_timeout = (
                write_timeout_ms
                if write_timeout_ms is not None
                else cc.write_timeout_ms
            )
            new_config = self._validate_and_create_config(
                new_baudrate,
                new_bytesize,
                new_parity,
                new_stopbits,
                new_flow,
                new_read_timeout,
                new_write_timeout,
            )

            # Apply the configuration (hot update)
            self._apply_config(managed, new_config)
            managed.config = new_config

            logger.info("Serial port configuration updated: %s", port)
            return PortStatus(
                port=port,
                is_open=True,
                config=new_config,
                connected=managed.is_connected,
                reconnecting=managed.reconnecting,
            )

    def _apply_config(self, managed: ManagedPort, config: SerialConfig) -> None:
        """Apply a configuration to an open serial port.

        Args:
            managed: The managed port object.
            config: New configuration.
        """
        ser = managed.serial

        # Map parity
        parity_map = {
            Parity.NONE: serial.PARITY_NONE,
            Parity.EVEN: serial.PARITY_EVEN,
            Parity.ODD: serial.PARITY_ODD,
            Parity.MARK: serial.PARITY_MARK,
            Parity.SPACE: serial.PARITY_SPACE,
        }

        # Map stop bits
        stopbits_map = {
            StopBits.ONE: serial.STOPBITS_ONE,
            StopBits.ONE_POINT_FIVE: serial.STOPBITS_ONE_POINT_FIVE,
            StopBits.TWO: serial.STOPBITS_TWO,
        }

        # Use apply_settings for hot update
        ser.apply_settings(
            {
                "baudrate": config.baudrate,
                "bytesize": config.bytesize,
                "parity": parity_map[config.parity],
                "stopbits": stopbits_map[config.stopbits],
                "xonxoff": config.flow_control == FlowControl.SOFTWARE,
                "rtscts": config.flow_control == FlowControl.HARDWARE,
            }
        )

        # Update timeout settings
        ser.timeout = config.read_timeout_ms / 1000.0
        ser.write_timeout = config.write_timeout_ms / 1000.0

    def get_status(self, port: str) -> PortStatus:
        """Return the status of a serial port.

        Args:
            port: Serial port path.

        Returns:
            Serial port status.

        Raises:
            PortClosedError: Serial port is not open.
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            return PortStatus(
                port=port,
                is_open=True,
                config=managed.config,
                connected=managed.is_connected,
                reconnecting=managed.reconnecting,
            )

    def get_all_status(self) -> list[PortStatus]:
        """Return the status of every open serial port.

        Returns:
            List of serial port statuses.
        """
        with self._lock:
            return [
                PortStatus(
                    port=port,
                    is_open=True,
                    config=managed.config,
                    connected=managed.is_connected,
                    reconnecting=managed.reconnecting,
                )
                for port, managed in self._ports.items()
            ]

    def send_data(self, port: str, data: bytes) -> int:
        """Send raw byte data.

        Args:
            port: Serial port path.
            data: Byte data to send.

        Returns:
            Number of bytes written.

        Raises:
            PortClosedError: Serial port is not open.
            WriteFailedError: Write failed.
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            try:
                result = managed.serial.write(data)
                bytes_written: int = result if result is not None else 0
                logger.debug("Sent data to serial port %s: %d bytes", port, bytes_written)
                return bytes_written
            except SerialException as e:
                logger.error("Serial port write failed: %s - %s", port, e)
                raise WriteFailedError(port, str(e)) from e

    def read_data(
        self, port: str, size: int | None = None, timeout_ms: int | None = None
    ) -> bytes:
        """Read raw byte data.

        Args:
            port: Serial port path.
            size: Number of bytes to read; None reads all available data.
            timeout_ms: Read timeout in ms; None uses the port's configured timeout.

        Returns:
            Raw bytes read.

        Raises:
            PortClosedError: Serial port is not open.
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            ser = managed.serial

            # Save the original timeout setting
            original_timeout = ser.timeout

            try:
                # If a timeout was supplied, apply it temporarily
                if timeout_ms is not None:
                    ser.timeout = timeout_ms / 1000.0

                data: bytes
                if size is not None:
                    # Read a fixed number of bytes
                    data = ser.read(size)
                else:
                    # Read all available data
                    available: int = ser.in_waiting
                    if available > 0:
                        data = ser.read(available)
                    else:
                        # No data available; try reading once (blocks up to timeout)
                        data = ser.read(1)
                        if data:
                            # If we got a byte, read whatever else is waiting
                            remaining: int = ser.in_waiting
                            if remaining > 0:
                                data += ser.read(remaining)

                logger.debug(
                    "Read data from serial port %s: %d bytes", port, len(data)
                )
                return data
            except SerialException as e:
                logger.error("Serial port read failed: %s - %s", port, e)
                raise PortClosedError(port) from e
            finally:
                # Restore the original timeout setting
                if timeout_ms is not None:
                    ser.timeout = original_timeout

    def shutdown(self) -> None:
        """Shut down the manager.

        Stops the reconnect thread and closes every open serial port.
        """
        self._running = False

        # Wait for the reconnect thread to finish
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5.0)

        # Close all serial ports
        with self._lock:
            for port, managed in list(self._ports.items()):
                try:
                    managed.serial.close()
                    logger.debug("Closed serial port: %s", port)
                except Exception as e:
                    logger.warning("Failed to close serial port: %s - %s", port, e)
            self._ports.clear()

        logger.info("Serial port manager has been shut down")


# Global serial port manager instance
_serial_manager: SerialManager | None = None


def get_serial_manager() -> SerialManager:
    """Return the serial port manager singleton.

    Returns:
        Serial port manager instance.
    """
    global _serial_manager
    if _serial_manager is None:
        _serial_manager = SerialManager()
    return _serial_manager
