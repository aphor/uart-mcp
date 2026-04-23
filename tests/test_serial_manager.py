"""Tests for the serial port manager."""

from unittest.mock import MagicMock, patch

import pytest

from uart_mcp.errors import (
    InvalidParamError,
    PortBlacklistedError,
    PortClosedError,
    WriteFailedError,
)
from uart_mcp.serial_manager import SerialManager


class TestSerialManagerListPorts:
    """Tests for list_ports."""

    def test_list_ports_empty(self, mock_list_ports):
        """Test with no available ports."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        ports = manager.list_ports()

        assert ports == []
        manager.shutdown()

    def test_list_ports_with_devices(self, mock_list_ports):
        """Test with ports available."""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "USB Serial"
        mock_port.hwid = "USB VID:PID=1234:5678"
        mock_list_ports.return_value = [mock_port]

        manager = SerialManager(enable_auto_reconnect=False)
        ports = manager.list_ports()

        assert len(ports) == 1
        assert ports[0].port == "/dev/ttyUSB0"
        assert ports[0].description == "USB Serial"
        manager.shutdown()


class TestSerialManagerOpenPort:
    """Tests for open_port."""

    def test_open_port_success(self, mock_serial, mock_list_ports):
        """Test successfully opening a port."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            status = manager.open_port("/dev/ttyUSB0")

            assert status.is_open is True
            assert status.port == "/dev/ttyUSB0"

        manager.shutdown()

    def test_open_port_idempotent(self, mock_serial, mock_list_ports):
        """Test opening the same port twice (idempotent)."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            # First open
            status1 = manager.open_port("/dev/ttyUSB0")
            # Second open (should return the current status)
            status2 = manager.open_port("/dev/ttyUSB0")

            assert status1.is_open is True
            assert status2.is_open is True
            # create_serial should only be called once
            assert mock_create.call_count == 1

        manager.shutdown()

    def test_open_port_invalid_baudrate(self, mock_list_ports):
        """Test an invalid baud rate."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(InvalidParamError) as exc_info:
            manager.open_port("/dev/ttyUSB0", baudrate=12345)

        assert exc_info.value.code.value == 1005
        manager.shutdown()

    def test_open_port_invalid_bytesize(self, mock_list_ports):
        """Test invalid data bits."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(InvalidParamError):
            manager.open_port("/dev/ttyUSB0", bytesize=9)

        manager.shutdown()

    def test_open_port_blacklisted(self, mock_list_ports):
        """Test opening a blacklisted port."""
        mock_list_ports.return_value = []

        with patch("uart_mcp.serial_manager.get_blacklist_manager") as mock_blacklist:
            mock_blacklist.return_value.is_blacklisted.return_value = True
            manager = SerialManager(enable_auto_reconnect=False)

            with pytest.raises(PortBlacklistedError):
                manager.open_port("/dev/ttyS0")

            manager.shutdown()


class TestSerialManagerClosePort:
    """Tests for close_port."""

    def test_close_port_success(self, mock_serial, mock_list_ports):
        """Test successfully closing a port."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            result = manager.close_port("/dev/ttyUSB0")

            assert result["success"] is True
            mock_serial_obj.close.assert_called_once()

        manager.shutdown()

    def test_close_port_not_open(self, mock_list_ports):
        """Test closing a port that is not open."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.close_port("/dev/ttyUSB0")

        manager.shutdown()


class TestSerialManagerSetConfig:
    """Tests for set_config."""

    def test_set_config_success(self, mock_serial, mock_list_ports):
        """Test successfully updating configuration."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0", baudrate=9600)
            status = manager.set_config("/dev/ttyUSB0", baudrate=115200)

            assert status.config.baudrate == 115200
            mock_serial_obj.apply_settings.assert_called()

        manager.shutdown()

    def test_set_config_not_open(self, mock_list_ports):
        """Test configuring a port that is not open."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.set_config("/dev/ttyUSB0", baudrate=115200)

        manager.shutdown()


class TestSerialManagerGetStatus:
    """Tests for get_status."""

    def test_get_status_success(self, mock_serial, mock_list_ports):
        """Test successfully fetching status."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            status = manager.get_status("/dev/ttyUSB0")

            assert status.is_open is True
            assert status.port == "/dev/ttyUSB0"

        manager.shutdown()

    def test_get_status_not_open(self, mock_list_ports):
        """Test fetching the status of a port that is not open."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.get_status("/dev/ttyUSB0")

        manager.shutdown()


class TestSerialManagerSendData:
    """Tests for send_data."""

    def test_send_data_success(self, mock_serial, mock_list_ports):
        """Test successfully sending data."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.write.return_value = 5
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            bytes_written = manager.send_data("/dev/ttyUSB0", b"hello")

            assert bytes_written == 5
            mock_serial_obj.write.assert_called_once_with(b"hello")

        manager.shutdown()

    def test_send_data_not_open(self, mock_list_ports):
        """Test sending data to a port that is not open."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.send_data("/dev/ttyUSB0", b"hello")

        manager.shutdown()

    def test_send_data_write_error(self, mock_serial, mock_list_ports):
        """Test a write failure."""
        from serial import SerialException

        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.write.side_effect = SerialException("write error")
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")

            with pytest.raises(WriteFailedError):
                manager.send_data("/dev/ttyUSB0", b"hello")

        manager.shutdown()


class TestSerialManagerReadData:
    """Tests for read_data."""

    def test_read_data_with_size(self, mock_serial, mock_list_ports):
        """Test reading a specific number of bytes."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"hello"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0", size=5)

            assert data == b"hello"
            mock_serial_obj.read.assert_called_once_with(5)

        manager.shutdown()

    def test_read_data_available(self, mock_serial, mock_list_ports):
        """Test reading all available data."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 10
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"0123456789"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0")

            assert data == b"0123456789"
            mock_serial_obj.read.assert_called_once_with(10)

        manager.shutdown()

    def test_read_data_with_timeout(self, mock_serial, mock_list_ports):
        """Test reading with a custom timeout."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 5
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"hello"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            manager.read_data("/dev/ttyUSB0", timeout_ms=500)  # return value ignored

            # Verify the timeout was only modified temporarily
            assert mock_serial_obj.timeout == 1.0  # should be restored

        manager.shutdown()

    def test_read_data_not_open(self, mock_list_ports):
        """Test reading from a port that is not open."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.read_data("/dev/ttyUSB0")

        manager.shutdown()

    def test_read_data_empty(self, mock_serial, mock_list_ports):
        """Test reading when no data is available."""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b""
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0")

            assert data == b""

        manager.shutdown()
