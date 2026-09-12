"""MCP Server implementation.

Provides the main server logic for the UART MCP Server.
"""

import asyncio
import json
import logging
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import ServerRequestContext
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .errors import SerialError
from .serial_manager import get_serial_manager
from .terminal_manager import get_terminal_manager
from .tools.data_ops import (
    READ_DATA_TOOL,
    SEND_DATA_TOOL,
    read_data,
    send_data,
)
from .tools.list_ports import LIST_PORTS_TOOL, list_ports
from .tools.port_ops import (
    CLOSE_PORT_TOOL,
    GET_STATUS_TOOL,
    OPEN_PORT_TOOL,
    SET_CONFIG_TOOL,
    close_port,
    get_status,
    open_port,
    set_config,
)
from .tools.terminal import (
    CLEAR_BUFFER_TOOL,
    CLOSE_SESSION_TOOL,
    CREATE_SESSION_TOOL,
    GET_SESSION_INFO_TOOL,
    LIST_SESSIONS_TOOL,
    READ_OUTPUT_TOOL,
    SEND_COMMAND_TOOL,
    clear_buffer,
    close_session,
    create_session,
    get_session_info,
    list_sessions,
    read_output,
    send_command,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def handle_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    """Return the list of available tools."""
    return types.ListToolsResult(tools=[
        types.Tool(
            name=LIST_PORTS_TOOL["name"],
            description=LIST_PORTS_TOOL["description"],
            input_schema=LIST_PORTS_TOOL["inputSchema"],
        ),
        types.Tool(
            name=OPEN_PORT_TOOL["name"],
            description=OPEN_PORT_TOOL["description"],
            input_schema=OPEN_PORT_TOOL["inputSchema"],
        ),
        types.Tool(
            name=CLOSE_PORT_TOOL["name"],
            description=CLOSE_PORT_TOOL["description"],
            input_schema=CLOSE_PORT_TOOL["inputSchema"],
        ),
        types.Tool(
            name=SET_CONFIG_TOOL["name"],
            description=SET_CONFIG_TOOL["description"],
            input_schema=SET_CONFIG_TOOL["inputSchema"],
        ),
        types.Tool(
            name=GET_STATUS_TOOL["name"],
            description=GET_STATUS_TOOL["description"],
            input_schema=GET_STATUS_TOOL["inputSchema"],
        ),
        types.Tool(
            name=SEND_DATA_TOOL["name"],
            description=SEND_DATA_TOOL["description"],
            input_schema=SEND_DATA_TOOL["inputSchema"],
        ),
        types.Tool(
            name=READ_DATA_TOOL["name"],
            description=READ_DATA_TOOL["description"],
            input_schema=READ_DATA_TOOL["inputSchema"],
        ),
        # Terminal session tools
        types.Tool(
            name=CREATE_SESSION_TOOL["name"],
            description=CREATE_SESSION_TOOL["description"],
            input_schema=CREATE_SESSION_TOOL["inputSchema"],
        ),
        types.Tool(
            name=CLOSE_SESSION_TOOL["name"],
            description=CLOSE_SESSION_TOOL["description"],
            input_schema=CLOSE_SESSION_TOOL["inputSchema"],
        ),
        types.Tool(
            name=SEND_COMMAND_TOOL["name"],
            description=SEND_COMMAND_TOOL["description"],
            input_schema=SEND_COMMAND_TOOL["inputSchema"],
        ),
        types.Tool(
            name=READ_OUTPUT_TOOL["name"],
            description=READ_OUTPUT_TOOL["description"],
            input_schema=READ_OUTPUT_TOOL["inputSchema"],
        ),
        types.Tool(
            name=LIST_SESSIONS_TOOL["name"],
            description=LIST_SESSIONS_TOOL["description"],
            input_schema=LIST_SESSIONS_TOOL["inputSchema"],
        ),
        types.Tool(
            name=GET_SESSION_INFO_TOOL["name"],
            description=GET_SESSION_INFO_TOOL["description"],
            input_schema=GET_SESSION_INFO_TOOL["inputSchema"],
        ),
        types.Tool(
            name=CLEAR_BUFFER_TOOL["name"],
            description=CLEAR_BUFFER_TOOL["description"],
            input_schema=CLEAR_BUFFER_TOOL["inputSchema"],
        ),
    ])


async def handle_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    """Handle a tool call."""
    name = params.name
    arguments = params.arguments or {}
    try:
        result: Any
        if name == "list_ports":
            result = list_ports()
        elif name == "open_port":
            result = open_port(**arguments)
        elif name == "close_port":
            result = close_port(**arguments)
        elif name == "set_config":
            result = set_config(**arguments)
        elif name == "get_status":
            result = get_status(**arguments)
        elif name == "send_data":
            result = send_data(**arguments)
        elif name == "read_data":
            result = read_data(**arguments)
        # Terminal session tools
        elif name == "create_session":
            result = create_session(**arguments)
        elif name == "close_session":
            result = close_session(**arguments)
        elif name == "send_command":
            result = send_command(**arguments)
        elif name == "read_output":
            result = read_output(**arguments)
        elif name == "list_sessions":
            result = list_sessions()
        elif name == "get_session_info":
            result = get_session_info(**arguments)
        elif name == "clear_buffer":
            result = clear_buffer(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        # Return the result as JSON
        text = json.dumps(result, ensure_ascii=False)
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)])

    except SerialError as e:
        # Serial port error: return the error information
        text = json.dumps(e.to_dict(), ensure_ascii=False)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)], is_error=True
        )

    except Exception as e:
        # Other errors
        error_response = {"error": {"code": -1, "message": f"Internal error: {e!s}"}}
        text = json.dumps(error_response, ensure_ascii=False)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)], is_error=True
        )


# Create the MCP server
server: Server = Server(
    "uart-mcp",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def run_server() -> None:
    """Run the MCP server."""
    logger.info("Starting UART MCP Server...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="uart-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        # Shut down the terminal manager
        terminal_mgr = get_terminal_manager()
        terminal_mgr.shutdown()
        # Shut down the serial port manager
        serial_mgr = get_serial_manager()
        serial_mgr.shutdown()
        logger.info("UART MCP Server shut down")


if __name__ == "__main__":
    main()
