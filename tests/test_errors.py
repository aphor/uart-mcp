"""Tests for the errors module."""

from uart_mcp.errors import (
    ErrorCode,
    InvalidParamError,
    PortBlacklistedError,
    PortBusyError,
    PortClosedError,
    PortNotFoundError,
    SerialError,
)


class TestErrorCode:
    """Test the error code enumeration."""

    def test_error_codes_values(self):
        """Test error code values."""
        assert ErrorCode.PORT_NOT_FOUND == 1001
        assert ErrorCode.PORT_BUSY == 1002
        assert ErrorCode.PORT_OPEN_FAILED == 1003
        assert ErrorCode.PORT_CLOSED == 1004
        assert ErrorCode.INVALID_PARAM == 1005
        assert ErrorCode.READ_TIMEOUT == 1006
        assert ErrorCode.WRITE_FAILED == 1007
        assert ErrorCode.PERMISSION_DENIED == 1008
        assert ErrorCode.PORT_BLACKLISTED == 1009


class TestSerialError:
    """Test the serial port base exception."""

    def test_serial_error_with_detail(self):
        """Test an exception raised with detail."""
        error = SerialError(ErrorCode.PORT_NOT_FOUND, "/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert "Serial port not found" in error.message
        assert "/dev/ttyUSB0" in error.message

    def test_serial_error_without_detail(self):
        """Test an exception raised without detail."""
        error = SerialError(ErrorCode.PORT_NOT_FOUND)
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert error.message == "Serial port not found"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = SerialError(ErrorCode.PORT_NOT_FOUND, "/dev/ttyUSB0")
        result = error.to_dict()
        assert result["error"]["code"] == 1001
        assert "Serial port not found" in result["error"]["message"]


class TestSpecificErrors:
    """Test specific exception classes."""

    def test_port_not_found_error(self):
        """Test the port-not-found exception."""
        error = PortNotFoundError("/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert "/dev/ttyUSB0" in error.message

    def test_port_busy_error(self):
        """Test the port-busy exception."""
        error = PortBusyError("COM1")
        assert error.code == ErrorCode.PORT_BUSY
        assert "COM1" in error.message

    def test_port_closed_error(self):
        """Test the port-closed exception."""
        error = PortClosedError("/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_CLOSED

    def test_invalid_param_error(self):
        """Test the invalid-parameter exception."""
        error = InvalidParamError("baudrate", -1, "must be positive")
        assert error.code == ErrorCode.INVALID_PARAM
        assert "baudrate" in error.message
        assert "-1" in error.message

    def test_port_blacklisted_error(self):
        """Test the port-blacklisted exception."""
        error = PortBlacklistedError("/dev/ttyS0")
        assert error.code == ErrorCode.PORT_BLACKLISTED
        assert "/dev/ttyS0" in error.message
