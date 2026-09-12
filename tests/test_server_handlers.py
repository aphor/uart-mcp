"""Tests for server.py handler functions.

Covers handle_list_tools and handle_call_tool.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as types
import pytest

# handle_list_tools/handle_call_tool ignore the request context entirely, so
# a placeholder stands in for the real ServerRequestContext the mcp runtime
# would otherwise construct per-request.
_CTX: Any = None


class TestHandleListTools:
    """Tests for handle_list_tools."""

    @pytest.mark.asyncio
    async def test_handle_list_tools_returns_all_tools(self):
        """Test that handle_list_tools returns all tools."""
        from uart_mcp.server import handle_list_tools

        result = await handle_list_tools(_CTX, None)
        tools = result.tools

        # Verify the returned tool list
        assert isinstance(tools, list)
        assert len(tools) == 14  # 14 tools total

        # Verify each tool has the required attributes
        tool_names = [tool.name for tool in tools]

        # Basic serial-port tools
        assert "list_ports" in tool_names
        assert "open_port" in tool_names
        assert "close_port" in tool_names
        assert "set_config" in tool_names
        assert "get_status" in tool_names

        # Data I/O tools
        assert "send_data" in tool_names
        assert "read_data" in tool_names

        # Terminal session tools
        assert "create_session" in tool_names
        assert "close_session" in tool_names
        assert "send_command" in tool_names
        assert "read_output" in tool_names
        assert "list_sessions" in tool_names
        assert "get_session_info" in tool_names
        assert "clear_buffer" in tool_names


async def _call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    """Invoke handle_call_tool with the mcp 2.x request-params signature."""
    from uart_mcp.server import handle_call_tool

    return await handle_call_tool(_CTX, types.CallToolRequestParams(name=name, arguments=arguments))


class TestHandleCallTool:
    """Tests for handle_call_tool."""

    @pytest.mark.asyncio
    async def test_call_list_ports(self, mock_list_ports_with_devices, reset_managers):
        """Test calling the list_ports tool."""
        result = await _call_tool("list_ports", {})

        assert len(result.content) == 1
        assert result.content[0].type == "text"

        data = json.loads(result.content[0].text)
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_call_open_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the open_port tool."""
        result = await _call_tool("open_port", {
            "port": "/dev/ttyMOCK0",
            "baudrate": 115200
        })

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("is_open") is True

    @pytest.mark.asyncio
    async def test_call_get_status(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the get_status tool."""
        # Open the port first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await _call_tool("get_status", {"port": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("is_open") is True

    @pytest.mark.asyncio
    async def test_call_set_config(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the set_config tool."""
        # Open the port first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await _call_tool("set_config", {
            "port": "/dev/ttyMOCK0",
            "baudrate": 9600
        })

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("config", {}).get("baudrate") == 9600

    @pytest.mark.asyncio
    async def test_call_send_data(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the send_data tool."""
        # Open the port first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await _call_tool("send_data", {
            "port": "/dev/ttyMOCK0",
            "data": "Hello",
            "is_binary": False
        })

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_read_data(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the read_data tool."""
        # Open the port and send data first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("send_data", {"port": "/dev/ttyMOCK0", "data": "Test", "is_binary": False})

        result = await _call_tool("read_data", {
            "port": "/dev/ttyMOCK0",
            "is_binary": False
        })

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "Test" in data.get("data", "")

    @pytest.mark.asyncio
    async def test_call_close_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the close_port tool."""
        # Open the port first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await _call_tool("close_port", {"port": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("success") is True

    # ========== Terminal session tool tests ==========

    @pytest.mark.asyncio
    async def test_call_create_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the create_session tool."""
        # Open the port first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("session_id") == "/dev/ttyMOCK0"

    @pytest.mark.asyncio
    async def test_call_list_sessions(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the list_sessions tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("list_sessions", {})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "sessions" in data

    @pytest.mark.asyncio
    async def test_call_get_session_info(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the get_session_info tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("get_session_info", {"session_id": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("session_id") == "/dev/ttyMOCK0"

    @pytest.mark.asyncio
    async def test_call_send_command(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the send_command tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("send_command", {
            "session_id": "/dev/ttyMOCK0",
            "command": "AT"
        })

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_read_output(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the read_output tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("read_output", {"session_id": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "data" in data

    @pytest.mark.asyncio
    async def test_call_clear_buffer(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the clear_buffer tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("clear_buffer", {"session_id": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_close_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """Test calling the close_session tool."""
        # Open the port and create a session first
        await _call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await _call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await _call_tool("close_session", {"session_id": "/dev/ttyMOCK0"})

        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert data.get("success") is True

    # ========== Error-handling tests ==========

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, reset_managers):
        """Test that calling an unknown tool returns an error."""
        result = await _call_tool("unknown_tool", {})

        assert result.is_error is True
        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "Unknown tool" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_serial_error_handling(self, reset_managers):
        """Test SerialError handling."""
        # Fetching the status of an unopened port should raise SerialError
        result = await _call_tool("get_status", {"port": "/dev/ttyNONEXIST"})

        assert result.is_error is True
        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "code" in data["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, reset_managers):
        """Test handling of a generic exception."""
        # Patch the correct module path to trigger a generic exception
        with patch("uart_mcp.server.list_ports", side_effect=RuntimeError("test exception")):
            result = await _call_tool("list_ports", {})

        assert result.is_error is True
        assert len(result.content) == 1
        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "Internal error" in data["error"]["message"]


class TestMainAndRunServer:
    """Tests for main() and run_server()."""

    @pytest.mark.asyncio
    async def test_run_server_starts_correctly(self):
        """Test that run_server starts and exits immediately."""
        from uart_mcp.server import run_server

        # Mock the stdio_server context manager so it returns immediately
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        async def mock_aenter(self):
            return (mock_read_stream, mock_write_stream)

        async def mock_aexit(self, *args):
            pass

        mock_context = MagicMock()
        mock_context.__aenter__ = mock_aenter
        mock_context.__aexit__ = mock_aexit

        with patch(
            "uart_mcp.server.mcp.server.stdio.stdio_server",
            return_value=mock_context
        ):
            with patch(
                "uart_mcp.server.server.run",
                new_callable=AsyncMock
            ) as mock_run:
                await run_server()
                mock_run.assert_called_once()

    def test_main_normal_exit(self):
        """Test that main starts and exits normally."""
        from uart_mcp.server import main

        def mock_asyncio_run_impl(coro):
            # Close the coroutine to avoid a warning
            coro.close()

        with patch(
            "uart_mcp.server.asyncio.run",
            side_effect=mock_asyncio_run_impl
        ) as mock_asyncio_run:
            with patch("uart_mcp.server.get_terminal_manager") as mock_term_mgr:
                with patch("uart_mcp.server.get_serial_manager") as mock_serial_mgr:
                    mock_term_instance = MagicMock()
                    mock_serial_instance = MagicMock()
                    mock_term_mgr.return_value = mock_term_instance
                    mock_serial_mgr.return_value = mock_serial_instance

                    main()

                    mock_asyncio_run.assert_called_once()
                    mock_term_instance.shutdown.assert_called_once()
                    mock_serial_instance.shutdown.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test that main handles KeyboardInterrupt."""
        from uart_mcp.server import main

        def mock_asyncio_run_impl(coro):
            # Close the coroutine to avoid a warning
            coro.close()
            raise KeyboardInterrupt

        with patch("uart_mcp.server.asyncio.run", side_effect=mock_asyncio_run_impl):
            with patch("uart_mcp.server.get_terminal_manager") as mock_term_mgr:
                with patch("uart_mcp.server.get_serial_manager") as mock_serial_mgr:
                    mock_term_instance = MagicMock()
                    mock_serial_instance = MagicMock()
                    mock_term_mgr.return_value = mock_term_instance
                    mock_serial_mgr.return_value = mock_serial_instance

                    # Should not raise
                    main()

                    # Ensure cleanup still runs
                    mock_term_instance.shutdown.assert_called_once()
                    mock_serial_instance.shutdown.assert_called_once()
