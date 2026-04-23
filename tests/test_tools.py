"""Tests for MCP tools."""

from unittest.mock import patch

from uart_mcp.tools.list_ports import list_ports
from uart_mcp.tools.port_ops import close_port, get_status, open_port, set_config
from uart_mcp.types import PortInfo, PortStatus, SerialConfig


class TestListPortsTool:
    """Tests for the list_ports tool."""

    def test_list_ports_returns_list(self):
        """Test that the result is a list."""
        with patch("uart_mcp.tools.list_ports.get_serial_manager") as mock_manager:
            mock_manager.return_value.list_ports.return_value = [
                PortInfo(
                    port="/dev/ttyUSB0", description="USB Serial", hwid="1234:5678"
                )
            ]

            result = list_ports()

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["port"] == "/dev/ttyUSB0"

    def test_list_ports_empty(self):
        """Test the empty-list case."""
        with patch("uart_mcp.tools.list_ports.get_serial_manager") as mock_manager:
            mock_manager.return_value.list_ports.return_value = []

            result = list_ports()

            assert result == []


class TestOpenPortTool:
    """Tests for the open_port tool."""

    def test_open_port_default_config(self):
        """Test opening with the default configuration."""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=SerialConfig(),
                connected=True,
            )
            mock_manager.return_value.open_port.return_value = mock_status

            result = open_port(port="/dev/ttyUSB0")

            assert result["is_open"] is True
            assert result["port"] == "/dev/ttyUSB0"

    def test_open_port_custom_config(self):
        """Test opening with a custom configuration."""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig(baudrate=115200)
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
                connected=True,
            )
            mock_manager.return_value.open_port.return_value = mock_status

            open_port(port="/dev/ttyUSB0", baudrate=115200)

            mock_manager.return_value.open_port.assert_called_once()
            call_kwargs = mock_manager.return_value.open_port.call_args[1]
            assert call_kwargs["baudrate"] == 115200


class TestClosePortTool:
    """Tests for the close_port tool."""

    def test_close_port_success(self):
        """Test successful close."""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            mock_manager.return_value.close_port.return_value = {
                "success": True,
                "port": "/dev/ttyUSB0",
            }

            result = close_port(port="/dev/ttyUSB0")

            assert result["success"] is True


class TestSetConfigTool:
    """Tests for the set_config tool."""

    def test_set_config_partial(self):
        """Test a partial configuration update."""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig(baudrate=115200)
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
            )
            mock_manager.return_value.set_config.return_value = mock_status

            result = set_config(port="/dev/ttyUSB0", baudrate=115200)

            assert result["config"]["baudrate"] == 115200


class TestGetStatusTool:
    """Tests for the get_status tool."""

    def test_get_status_success(self):
        """Test successful status retrieval."""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig()
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
                connected=True,
                reconnecting=False,
            )
            mock_manager.return_value.get_status.return_value = mock_status

            result = get_status(port="/dev/ttyUSB0")

            assert result["is_open"] is True
            assert result["connected"] is True
            assert result["reconnecting"] is False
