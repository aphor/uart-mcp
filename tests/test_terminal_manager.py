"""Tests for the terminal manager."""

from unittest.mock import MagicMock, patch

import pytest

from uart_mcp.errors import (
    InvalidLineEndingError,
    PortNotOpenError,
    SessionExistsError,
    SessionNotFoundError,
)
from uart_mcp.terminal_manager import TerminalManager, TerminalSession
from uart_mcp.types import LineEnding


class TestTerminalSession:
    """Tests for the TerminalSession class."""

    def test_session_init(self):
        """Test session initialization."""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding.CRLF,
            local_echo=False,
            buffer_size=65536,
        )

        assert session.session_id == "/dev/ttyUSB0"
        assert session.port == "/dev/ttyUSB0"
        assert session.config.line_ending == LineEnding.CRLF
        assert session.config.local_echo is False
        assert session.config.buffer_size == 65536
        assert session.is_active is False

    def test_session_buffer_operations(self):
        """Test buffer operations."""
        session = TerminalSession(port="/dev/ttyUSB0")

        # Manually append data to the buffer
        session._append_to_buffer(b"hello")
        session._append_to_buffer(b" world")

        assert session.buffer_length == 11

        # Read data (clear)
        data = session.read_output(clear=True)
        assert data == b"hello world"
        assert session.buffer_length == 0

    def test_session_buffer_overflow(self):
        """Test buffer overflow handling."""
        # Create a small buffer
        session = TerminalSession(port="/dev/ttyUSB0", buffer_size=10)

        # Append data that exceeds the buffer capacity
        session._append_to_buffer(b"12345")
        session._append_to_buffer(b"67890")
        session._append_to_buffer(b"ABCDE")

        # Buffer should drop older data
        assert session.buffer_length <= 10

    def test_session_clear_buffer(self):
        """Test clearing the buffer."""
        session = TerminalSession(port="/dev/ttyUSB0")

        session._append_to_buffer(b"test data")
        session.clear_buffer()

        assert session.buffer_length == 0
        assert session.read_output() == b""

    def test_session_get_info(self):
        """Test fetching session info."""
        session = TerminalSession(port="/dev/ttyUSB0")
        session._append_to_buffer(b"test")

        info = session.get_info()

        assert info.session_id == "/dev/ttyUSB0"
        assert info.port == "/dev/ttyUSB0"
        assert info.buffer_size == 4
        assert info.is_active is False

    def test_session_send_command_with_line_ending(self):
        """Test sending a command with a line ending."""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding.CRLF,
            local_echo=True,
        )

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = 7

            bytes_written = session.send_command("test", add_line_ending=True)

            assert bytes_written == 7
            # Verify the sent data includes the line ending
            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"test\r\n"
            )

            # Verify local echo
            assert session.buffer_length == 6  # "test\r\n"

    def test_session_send_command_without_line_ending(self):
        """Test sending a command without a line ending."""
        session = TerminalSession(port="/dev/ttyUSB0")

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = 4

            bytes_written = session.send_command("test", add_line_ending=False)

            assert bytes_written == 4
            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"test"
            )


class TestTerminalManager:
    """Tests for the TerminalManager class."""

    def test_create_session_success(self):
        """Test creating a session successfully."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            # Have read_data raise, so the background thread exits
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            info = manager.create_session(
                port="/dev/ttyUSB0",
                line_ending="CRLF",
            )

            assert info.session_id == "/dev/ttyUSB0"
            assert info.port == "/dev/ttyUSB0"
            assert info.config.line_ending.name == "CRLF"

        manager.shutdown()

    def test_create_session_already_exists(self):
        """Test creating a session that already exists."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")

            with pytest.raises(SessionExistsError):
                manager.create_session(port="/dev/ttyUSB0")

        manager.shutdown()

    def test_create_session_port_not_open(self):
        """Test creating a session on a port that is not open."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.side_effect = Exception("not open")

            with pytest.raises(PortNotOpenError):
                manager.create_session(port="/dev/ttyUSB0")

        manager.shutdown()

    def test_create_session_invalid_line_ending(self):
        """Test an invalid line-ending configuration."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()

            with pytest.raises(InvalidLineEndingError):
                manager.create_session(port="/dev/ttyUSB0", line_ending="INVALID")

        manager.shutdown()

    def test_close_session_success(self):
        """Test closing a session successfully."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")
            result = manager.close_session("/dev/ttyUSB0")

            assert result["success"] is True
            assert result["session_id"] == "/dev/ttyUSB0"

        manager.shutdown()

    def test_close_session_not_found(self):
        """Test closing a session that does not exist."""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.close_session("/dev/ttyUSB0")

        manager.shutdown()

    def test_send_command_success(self):
        """Test sending a command successfully."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            # Have read_data return empty data so the background thread keeps running
            mock_serial_mgr.return_value.read_data.return_value = b""
            mock_serial_mgr.return_value.send_data.return_value = 7

            manager.create_session(port="/dev/ttyUSB0")
            result = manager.send_command("/dev/ttyUSB0", "test")

            assert result["success"] is True
            assert result["bytes_written"] == 7

        manager.shutdown()

    def test_send_command_session_not_found(self):
        """Test sending a command to a session that does not exist."""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.send_command("/dev/ttyUSB0", "test")

        manager.shutdown()

    def test_read_output_success(self):
        """Test reading output successfully."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")

            # Manually add data to the buffer
            session = manager.get_session("/dev/ttyUSB0")
            session._append_to_buffer(b"test output")

            result = manager.read_output("/dev/ttyUSB0")

            assert result["data"] == "test output"
            assert result["bytes_read"] == 11

        manager.shutdown()

    def test_clear_buffer_success(self):
        """Test clearing the buffer successfully."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")

            session = manager.get_session("/dev/ttyUSB0")
            session._append_to_buffer(b"test data")

            result = manager.clear_buffer("/dev/ttyUSB0")

            assert result["success"] is True
            assert session.buffer_length == 0

        manager.shutdown()

    def test_list_sessions(self):
        """Test listing all sessions."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")
            manager.create_session(port="/dev/ttyUSB1")

            sessions = manager.list_sessions()

            assert len(sessions) == 2
            session_ids = [s["session_id"] for s in sessions]
            assert "/dev/ttyUSB0" in session_ids
            assert "/dev/ttyUSB1" in session_ids

        manager.shutdown()

    def test_get_session_info_success(self):
        """Test fetching session info."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")
            info = manager.get_session_info("/dev/ttyUSB0")

            assert info["session_id"] == "/dev/ttyUSB0"
            assert info["port"] == "/dev/ttyUSB0"

        manager.shutdown()

    def test_get_session_info_not_found(self):
        """Test fetching info for a session that does not exist."""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.get_session_info("/dev/ttyUSB0")

        manager.shutdown()

    def test_shutdown(self):
        """Test shutting down the manager."""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("test")

            manager.create_session(port="/dev/ttyUSB0")
            manager.create_session(port="/dev/ttyUSB1")

            manager.shutdown()

            assert len(manager._sessions) == 0


class TestLineEndingConfigurations:
    """Test different line-ending configurations."""

    @pytest.mark.parametrize(
        "line_ending,expected_suffix",
        [
            ("CR", b"\r"),
            ("LF", b"\n"),
            ("CRLF", b"\r\n"),
        ],
    )
    def test_different_line_endings(self, line_ending, expected_suffix):
        """Test different line endings."""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding[line_ending],
        )

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = len(b"cmd" + expected_suffix)

            session.send_command("cmd", add_line_ending=True)

            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"cmd" + expected_suffix
            )
