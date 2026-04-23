"""Tests for terminal tools."""

from unittest.mock import MagicMock, patch

import pytest

from uart_mcp.tools.terminal import (
    clear_buffer,
    close_session,
    create_session,
    get_session_info,
    list_sessions,
    read_output,
    send_command,
)


@pytest.fixture
def mock_terminal_manager():
    """Mock the terminal manager."""
    with patch("uart_mcp.tools.terminal.get_terminal_manager") as mock:
        yield mock


class TestCreateSession:
    """Tests for the create_session tool."""

    def test_create_session_success(self, mock_terminal_manager):
        """Test creating a session successfully."""
        mock_info = MagicMock()
        mock_info.to_dict.return_value = {
            "session_id": "/dev/ttyUSB0",
            "port": "/dev/ttyUSB0",
            "config": {"line_ending": "CRLF"},
        }
        mock_terminal_manager.return_value.create_session.return_value = mock_info

        result = create_session(port="/dev/ttyUSB0")

        assert result["session_id"] == "/dev/ttyUSB0"
        mock_terminal_manager.return_value.create_session.assert_called_once_with(
            port="/dev/ttyUSB0",
            line_ending="CRLF",
            local_echo=False,
            buffer_size=65536,
        )

    def test_create_session_with_options(self, mock_terminal_manager):
        """Test creating a session with custom options."""
        mock_info = MagicMock()
        mock_info.to_dict.return_value = {"session_id": "/dev/ttyUSB0"}
        mock_terminal_manager.return_value.create_session.return_value = mock_info

        create_session(
            port="/dev/ttyUSB0",
            line_ending="LF",
            local_echo=True,
            buffer_size=32768,
        )

        mock_terminal_manager.return_value.create_session.assert_called_once_with(
            port="/dev/ttyUSB0",
            line_ending="LF",
            local_echo=True,
            buffer_size=32768,
        )


class TestCloseSession:
    """Tests for the close_session tool."""

    def test_close_session_success(self, mock_terminal_manager):
        """Test closing a session successfully."""
        mock_terminal_manager.return_value.close_session.return_value = {
            "success": True,
            "session_id": "/dev/ttyUSB0",
        }

        result = close_session(session_id="/dev/ttyUSB0")

        assert result["success"] is True
        mock_terminal_manager.return_value.close_session.assert_called_once_with(
            "/dev/ttyUSB0"
        )


class TestSendCommand:
    """Tests for the send_command tool."""

    def test_send_command_success(self, mock_terminal_manager):
        """Test sending a command successfully."""
        mock_terminal_manager.return_value.send_command.return_value = {
            "success": True,
            "bytes_written": 10,
        }

        result = send_command(session_id="/dev/ttyUSB0", command="ls -la")

        assert result["success"] is True
        assert result["bytes_written"] == 10
        mock_terminal_manager.return_value.send_command.assert_called_once_with(
            session_id="/dev/ttyUSB0",
            command="ls -la",
            add_line_ending=True,
        )

    def test_send_command_without_line_ending(self, mock_terminal_manager):
        """Test sending a command without a line ending."""
        mock_terminal_manager.return_value.send_command.return_value = {
            "success": True,
            "bytes_written": 6,
        }

        send_command(
            session_id="/dev/ttyUSB0",
            command="ls -la",
            add_line_ending=False,
        )

        mock_terminal_manager.return_value.send_command.assert_called_once_with(
            session_id="/dev/ttyUSB0",
            command="ls -la",
            add_line_ending=False,
        )


class TestReadOutput:
    """Tests for the read_output tool."""

    def test_read_output_success(self, mock_terminal_manager):
        """Test reading output successfully."""
        mock_terminal_manager.return_value.read_output.return_value = {
            "data": "test output\n",
            "bytes_read": 12,
        }

        result = read_output(session_id="/dev/ttyUSB0")

        assert result["data"] == "test output\n"
        assert result["bytes_read"] == 12
        mock_terminal_manager.return_value.read_output.assert_called_once_with(
            session_id="/dev/ttyUSB0",
            clear=True,
        )

    def test_read_output_without_clear(self, mock_terminal_manager):
        """Test reading output without clearing the buffer."""
        mock_terminal_manager.return_value.read_output.return_value = {
            "data": "test",
            "bytes_read": 4,
        }

        read_output(session_id="/dev/ttyUSB0", clear=False)

        mock_terminal_manager.return_value.read_output.assert_called_once_with(
            session_id="/dev/ttyUSB0",
            clear=False,
        )


class TestListSessions:
    """Tests for the list_sessions tool."""

    def test_list_sessions_empty(self, mock_terminal_manager):
        """Test an empty session list."""
        mock_terminal_manager.return_value.list_sessions.return_value = []

        result = list_sessions()

        assert result["sessions"] == []
        assert result["count"] == 0

    def test_list_sessions_with_data(self, mock_terminal_manager):
        """Test a non-empty session list."""
        mock_terminal_manager.return_value.list_sessions.return_value = [
            {"session_id": "/dev/ttyUSB0"},
            {"session_id": "/dev/ttyUSB1"},
        ]

        result = list_sessions()

        assert len(result["sessions"]) == 2
        assert result["count"] == 2


class TestGetSessionInfo:
    """Tests for the get_session_info tool."""

    def test_get_session_info_success(self, mock_terminal_manager):
        """Test fetching session info successfully."""
        mock_terminal_manager.return_value.get_session_info.return_value = {
            "session_id": "/dev/ttyUSB0",
            "port": "/dev/ttyUSB0",
            "buffer_size": 100,
            "is_active": True,
        }

        result = get_session_info(session_id="/dev/ttyUSB0")

        assert result["session_id"] == "/dev/ttyUSB0"
        assert result["is_active"] is True
        mock_terminal_manager.return_value.get_session_info.assert_called_once_with(
            "/dev/ttyUSB0"
        )


class TestClearBuffer:
    """Tests for the clear_buffer tool."""

    def test_clear_buffer_success(self, mock_terminal_manager):
        """Test clearing the buffer successfully."""
        mock_terminal_manager.return_value.clear_buffer.return_value = {
            "success": True,
            "session_id": "/dev/ttyUSB0",
        }

        result = clear_buffer(session_id="/dev/ttyUSB0")

        assert result["success"] is True
        mock_terminal_manager.return_value.clear_buffer.assert_called_once_with(
            "/dev/ttyUSB0"
        )
