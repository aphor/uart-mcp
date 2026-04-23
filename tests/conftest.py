"""pytest configuration and shared fixtures."""

import threading
from unittest.mock import MagicMock, patch

import pytest


class MockSerialLoopback:
    """Mock Serial class that simulates a serial loopback.

    Data written is automatically fed back into the read buffer, simulating
    the loopback effect of physically tying TX to RX.
    """

    def __init__(self, port=None, baudrate=9600, bytesize=8, parity='N',
                 stopbits=1, timeout=None, write_timeout=None,
                 xonxoff=False, rtscts=False, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts

        self._is_open = True
        self._buffer = bytearray()  # Loopback buffer
        self._lock = threading.Lock()

    @property
    def is_open(self):
        return self._is_open

    @property
    def in_waiting(self):
        with self._lock:
            return len(self._buffer)

    def open(self):
        self._is_open = True

    def close(self):
        self._is_open = False

    def write(self, data):
        """Write data and also push it into the read buffer (loopback)."""
        if not self._is_open:
            raise Exception("Serial port is not open")
        if isinstance(data, str):
            data = data.encode('utf-8')
        with self._lock:
            self._buffer.extend(data)
        return len(data)

    def read(self, size=1):
        """Read data from the buffer."""
        if not self._is_open:
            raise Exception("Serial port is not open")
        with self._lock:
            data = bytes(self._buffer[:size])
            self._buffer = self._buffer[size:]
        return data

    def read_all(self):
        """Read all available data."""
        with self._lock:
            data = bytes(self._buffer)
            self._buffer.clear()
        return data

    def reset_input_buffer(self):
        """Clear the input buffer."""
        with self._lock:
            self._buffer.clear()

    def reset_output_buffer(self):
        """Clear the output buffer (simulated)."""
        pass

    def flush(self):
        """Flush output."""
        pass

    def apply_settings(self, settings):
        """Apply configuration settings (hot update)."""
        if "baudrate" in settings:
            self.baudrate = settings["baudrate"]
        if "bytesize" in settings:
            self.bytesize = settings["bytesize"]
        if "parity" in settings:
            self.parity = settings["parity"]
        if "stopbits" in settings:
            self.stopbits = settings["stopbits"]
        if "xonxoff" in settings:
            self.xonxoff = settings["xonxoff"]
        if "rtscts" in settings:
            self.rtscts = settings["rtscts"]


class MockPortInfo:
    """Mock serial port info object."""
    def __init__(self, device, description="Mock serial port", hwid="MOCK_HWID"):
        self.device = device
        self.description = description
        self.hwid = hwid


@pytest.fixture
def mock_serial():
    """Mock a pyserial Serial object."""
    with patch("serial.Serial") as mock:
        serial_instance = MagicMock()
        serial_instance.is_open = True
        serial_instance.in_waiting = 0
        mock.return_value = serial_instance
        yield mock


@pytest.fixture
def mock_serial_loopback():
    """Mock a serial loopback: written data is fed back into the read buffer.

    Used by integration tests to simulate the loopback behavior of real hardware.
    """
    mock_instances = {}

    def create_mock_serial(*args, **kwargs):
        port = kwargs.get('port') or (args[0] if args else '/dev/mock')
        if port not in mock_instances:
            mock_instances[port] = MockSerialLoopback(*args, **kwargs)
        return mock_instances[port]

    with patch("serial.Serial", side_effect=create_mock_serial):
        yield mock_instances


@pytest.fixture
def mock_list_ports():
    """Mock serial.tools.list_ports.comports()."""
    with patch("serial.tools.list_ports.comports") as mock:
        yield mock


@pytest.fixture
def mock_list_ports_with_devices():
    """Mock list_ports to return a list of devices."""
    mock_ports = [
        MockPortInfo("/dev/ttyMOCK0", "Mock USB serial port", "USB VID:PID=1234:5678"),
        MockPortInfo(
            "/dev/ttyMOCK1", "Mock Bluetooth serial port", "BT ADDR=00:11:22:33:44:55"
        ),
    ]
    with patch("serial.tools.list_ports.comports", return_value=mock_ports):
        yield mock_ports


@pytest.fixture
def mock_blacklist_empty():
    """Mock an empty blacklist."""
    with patch("uart_mcp.config.get_blacklist_path") as mock_path:
        mock_path.return_value.exists.return_value = False
        yield mock_path


@pytest.fixture
def reset_managers():
    """Reset global manager state to isolate tests."""
    # Save the original state
    from uart_mcp import serial_manager, terminal_manager

    old_serial = serial_manager._serial_manager
    old_terminal = terminal_manager._terminal_manager

    # Reset to None
    serial_manager._serial_manager = None
    terminal_manager._terminal_manager = None

    yield

    # Clean up newly created managers
    try:
        if serial_manager._serial_manager is not None:
            serial_manager._serial_manager.shutdown()
    except Exception:
        pass
    try:
        if terminal_manager._terminal_manager is not None:
            terminal_manager._terminal_manager.shutdown()
    except Exception:
        pass

    # Restore the original state
    serial_manager._serial_manager = old_serial
    terminal_manager._terminal_manager = old_terminal
