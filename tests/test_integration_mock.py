"""Mock-based integration tests.

Simulates serial loopback so that all MCP tool functions can be tested without
real hardware. Suitable for automated testing in CI/CD environments.

Usage:
    pytest tests/test_integration_mock.py -v
"""

import base64
import time

import pytest

# Test configuration
MOCK_PORT = "/dev/ttyMOCK0"
MOCK_BAUDRATE = 115200


class TestMockIntegration:
    """Mock-based integration test class."""

    # ========== Phase 1: basic serial-port operations ==========

    def test_list_ports(self, mock_list_ports_with_devices, reset_managers):
        """Test listing all available serial ports."""
        from uart_mcp.tools.list_ports import list_ports

        ports = list_ports()

        assert len(ports) == 2
        port_names = [p["port"] for p in ports]
        assert MOCK_PORT in port_names
        assert "/dev/ttyMOCK1" in port_names

    def test_open_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test opening a serial port."""
        from uart_mcp.tools.port_ops import open_port

        result = open_port(
            port=MOCK_PORT,
            baudrate=MOCK_BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1.0,
        )

        assert result.get("is_open") is True
        assert result.get("port") == MOCK_PORT

    def test_get_status(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test fetching serial port status."""
        from uart_mcp.tools.port_ops import get_status, open_port

        # Open the port first
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = get_status(port=MOCK_PORT)

        assert result.get("is_open") is True
        config = result.get("config", {})
        assert config.get("baudrate") == MOCK_BAUDRATE

    def test_set_config(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test modifying serial port config (hot update)."""
        from uart_mcp.tools.port_ops import get_status, open_port, set_config

        # Open the port first
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # Change the baud rate
        new_baudrate = 9600
        result = set_config(port=MOCK_PORT, baudrate=new_baudrate)

        config = result.get("config", {})
        assert config.get("baudrate") == new_baudrate

        # Verify the config was updated
        status = get_status(port=MOCK_PORT)
        assert status.get("config", {}).get("baudrate") == new_baudrate

    def test_close_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test closing a serial port."""
        from uart_mcp.tools.port_ops import close_port, open_port

        # Open the port first
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = close_port(port=MOCK_PORT)

        assert result.get("success") is True

    # ========== Phase 2: data communication (loopback) ==========

    def test_send_receive_text(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test sending and receiving text data (loopback test)."""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import open_port

        # Open the port
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        test_message = "Hello UART!"

        # Send data
        send_result = send_data(port=MOCK_PORT, data=test_message, is_binary=False)
        assert send_result.get("success") is True

        # Read data (loopback)
        read_result = read_data(port=MOCK_PORT, is_binary=False)
        received = read_result.get("data", "")

        assert test_message in received

    def test_send_receive_binary(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test sending and receiving binary data (loopback test)."""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import open_port

        # Open the port
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # Prepare binary data
        raw_data = bytes([0x01, 0x02, 0x03, 0xFE, 0xFF])
        b64_data = base64.b64encode(raw_data).decode("ascii")

        # Send binary data
        send_result = send_data(port=MOCK_PORT, data=b64_data, is_binary=True)
        assert send_result.get("success") is True

        # Read binary data (loopback)
        read_result = read_data(port=MOCK_PORT, is_binary=True)
        received_b64 = read_result.get("data", "")
        received_raw = base64.b64decode(received_b64) if received_b64 else b""

        assert raw_data == received_raw

    # ========== Phase 3: terminal session tests ==========

    def test_create_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test creating a terminal session."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session

        # Open the port first
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = create_session(
            port=MOCK_PORT,
            line_ending="CRLF",
            local_echo=False,
        )

        assert result.get("session_id") == MOCK_PORT

    def test_list_sessions(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test listing all sessions."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session, list_sessions

        # Open the port and create a session
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = list_sessions()
        sessions = result.get("sessions", [])

        session_ids = [s.get("session_id") if isinstance(s, dict) else s for s in sessions]
        assert MOCK_PORT in session_ids

    def test_get_session_info(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test fetching session info."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session, get_session_info

        # Open the port and create a session
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = get_session_info(session_id=MOCK_PORT)

        assert result.get("session_id") == MOCK_PORT

    def test_send_command_read_output(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test sending a command and reading the output (loopback test)."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import (
            clear_buffer,
            create_session,
            read_output,
            send_command,
        )

        # Open the port and create a session
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        # Clear the buffer
        clear_buffer(session_id=MOCK_PORT)

        test_cmd = "AT"

        # Send the command
        send_result = send_command(
            session_id=MOCK_PORT,
            command=test_cmd,
            add_line_ending=True,
        )
        assert send_result.get("success") is True

        # Wait for the background thread to read the data
        time.sleep(0.2)

        # Read output (in loopback mode the sent command should come back)
        read_result = read_output(session_id=MOCK_PORT, clear=False)
        output = read_result.get("data", "")

        assert test_cmd in output

    def test_clear_buffer(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test clearing the buffer."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import clear_buffer, create_session, read_output

        # Open the port and create a session
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = clear_buffer(session_id=MOCK_PORT)
        assert result.get("success") is True

        # Verify the buffer is empty
        read_result = read_output(session_id=MOCK_PORT, clear=False)
        assert len(read_result.get("data", "")) == 0

    def test_close_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test closing a terminal session."""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import close_session, create_session

        # Open the port and create a session
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = close_session(session_id=MOCK_PORT)

        assert result.get("success") is True

    # ========== Phase 4: error-handling tests ==========

    def test_open_nonexistent_port(self, mock_list_ports_with_devices, reset_managers):
        """Test opening a port that does not exist (not in the port list)."""
        from uart_mcp.errors import PortNotFoundError
        from uart_mcp.tools.port_ops import open_port

        # No mock_serial_loopback — let it try to open a genuinely absent port
        with pytest.raises((PortNotFoundError, Exception)):
            open_port(port="/dev/ttyNONEXIST_CICD_TEST", baudrate=9600)

    def test_get_status_unopened_port(self, reset_managers):
        """Test fetching the status of a port that has not been opened."""
        from uart_mcp.tools.port_ops import get_status

        with pytest.raises(Exception):
            get_status(port=MOCK_PORT)

    def test_send_data_unopened_port(self, reset_managers):
        """Test sending data to a port that has not been opened."""
        from uart_mcp.tools.data_ops import send_data

        with pytest.raises(Exception):
            send_data(port=MOCK_PORT, data="test", is_binary=False)


class TestMockIntegrationWorkflow:
    """Full end-to-end workflow tests."""

    def test_full_workflow(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test the complete serial communication workflow."""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import (
            close_port,
            get_status,
            open_port,
            set_config,
        )
        from uart_mcp.tools.terminal import (
            clear_buffer,
            close_session,
            create_session,
            get_session_info,
            list_sessions,
            read_output,
            send_command,
        )

        # 1. Open port
        result = open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        assert result.get("is_open") is True

        # 2. Get status
        status = get_status(port=MOCK_PORT)
        assert status.get("is_open") is True

        # 3. Change config
        new_config = set_config(port=MOCK_PORT, baudrate=9600)
        assert new_config.get("config", {}).get("baudrate") == 9600

        # Restore config
        set_config(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # 4. Send / receive text
        send_data(port=MOCK_PORT, data="Hello", is_binary=False)
        read_result = read_data(port=MOCK_PORT, is_binary=False)
        assert "Hello" in read_result.get("data", "")

        # 5. Send / receive binary
        raw = bytes([0xAA, 0xBB])
        send_data(port=MOCK_PORT, data=base64.b64encode(raw).decode(), is_binary=True)
        read_result = read_data(port=MOCK_PORT, is_binary=True)
        assert base64.b64decode(read_result.get("data", "")) == raw

        # 6. Create terminal session
        session = create_session(port=MOCK_PORT)
        assert session.get("session_id") == MOCK_PORT

        # 7. List sessions
        sessions = list_sessions()
        assert len(sessions.get("sessions", [])) > 0

        # 8. Get session info
        info = get_session_info(session_id=MOCK_PORT)
        assert info.get("session_id") == MOCK_PORT

        # 9. Send command
        clear_buffer(session_id=MOCK_PORT)
        send_command(session_id=MOCK_PORT, command="TEST")
        time.sleep(0.2)
        output = read_output(session_id=MOCK_PORT)
        assert "TEST" in output.get("data", "")

        # 10. Clear buffer
        clear_buffer(session_id=MOCK_PORT)
        output = read_output(session_id=MOCK_PORT)
        assert output.get("data", "") == ""

        # 11. Close session
        close_session(session_id=MOCK_PORT)

        # 12. Close port
        result = close_port(port=MOCK_PORT)
        assert result.get("success") is True
