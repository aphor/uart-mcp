"""Terminal session tool implementation.

Provides creation, management, and data send/receive for terminal sessions.
"""

from typing import Any

from ..terminal_manager import get_terminal_manager
from ..types import DEFAULT_BUFFER_SIZE, DEFAULT_LOCAL_ECHO


def create_session(
    port: str,
    line_ending: str = "CRLF",
    local_echo: bool = DEFAULT_LOCAL_ECHO,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> dict[str, Any]:
    """Create a terminal session on an already-open serial port.

    Args:
        port: Serial port path.
        line_ending: Line-ending type (CR/LF/CRLF).
        local_echo: Whether to locally echo input.
        buffer_size: Output buffer size.

    Returns:
        Session information.
    """
    manager = get_terminal_manager()
    session_info = manager.create_session(
        port=port,
        line_ending=line_ending,
        local_echo=local_echo,
        buffer_size=buffer_size,
    )
    return session_info.to_dict()


def close_session(session_id: str) -> dict[str, Any]:
    """Close the specified terminal session.

    Args:
        session_id: Session ID (serial port path).

    Returns:
        Operation result.
    """
    manager = get_terminal_manager()
    return manager.close_session(session_id)


def send_command(
    session_id: str,
    command: str,
    add_line_ending: bool = True,
) -> dict[str, Any]:
    """Send a command to a terminal.

    Args:
        session_id: Session ID (serial port path).
        command: Command to send.
        add_line_ending: Whether to automatically append the line ending.

    Returns:
        Send result.
    """
    manager = get_terminal_manager()
    return manager.send_command(
        session_id=session_id,
        command=command,
        add_line_ending=add_line_ending,
    )


def read_output(
    session_id: str,
    clear: bool = True,
) -> dict[str, Any]:
    """Read the contents of the terminal output buffer.

    Args:
        session_id: Session ID (serial port path).
        clear: Whether to clear the buffer after reading.

    Returns:
        Output content.
    """
    manager = get_terminal_manager()
    return manager.read_output(session_id=session_id, clear=clear)


def list_sessions() -> dict[str, Any]:
    """List all active sessions.

    Returns:
        Session list.
    """
    manager = get_terminal_manager()
    sessions = manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


def get_session_info(session_id: str) -> dict[str, Any]:
    """Return detailed session information.

    Args:
        session_id: Session ID (serial port path).

    Returns:
        Session information.
    """
    manager = get_terminal_manager()
    return manager.get_session_info(session_id)


def clear_buffer(session_id: str) -> dict[str, Any]:
    """Clear the session's output buffer.

    Args:
        session_id: Session ID (serial port path).

    Returns:
        Operation result.
    """
    manager = get_terminal_manager()
    return manager.clear_buffer(session_id)


# Tool definitions (used for MCP registration)

CREATE_SESSION_TOOL: dict[str, Any] = {
    "name": "create_session",
    "description": (
        "Create a terminal session on an open serial port. Supports configurable "
        "line ending and local echo."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path, e.g. /dev/ttyUSB0 or COM1",
            },
            "line_ending": {
                "type": "string",
                "description": (
                    "Line-ending type: CR (carriage return), LF (line feed), or "
                    "CRLF (carriage return + line feed)."
                ),
                "enum": ["CR", "LF", "CRLF"],
                "default": "CRLF",
            },
            "local_echo": {
                "type": "boolean",
                "description": "Whether to locally echo the commands that are sent.",
                "default": False,
            },
            "buffer_size": {
                "type": "integer",
                "description": "Output buffer size in bytes. Default 64KB.",
                "default": DEFAULT_BUFFER_SIZE,
            },
        },
        "required": ["port"],
    },
}

CLOSE_SESSION_TOOL: dict[str, Any] = {
    "name": "close_session",
    "description": "Close the specified terminal session.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID (the serial port path), e.g. /dev/ttyUSB0 or COM1"
                ),
            },
        },
        "required": ["session_id"],
    },
}

SEND_COMMAND_TOOL: dict[str, Any] = {
    "name": "send_command",
    "description": (
        "Send a command to a terminal, optionally appending a line ending."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID (the serial port path), e.g. /dev/ttyUSB0 or COM1"
                ),
            },
            "command": {
                "type": "string",
                "description": "Command content to send",
            },
            "add_line_ending": {
                "type": "boolean",
                "description": "Whether to automatically append the line ending.",
                "default": True,
            },
        },
        "required": ["session_id", "command"],
    },
}

READ_OUTPUT_TOOL: dict[str, Any] = {
    "name": "read_output",
    "description": "Read the contents of the terminal output buffer.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID (the serial port path), e.g. /dev/ttyUSB0 or COM1"
                ),
            },
            "clear": {
                "type": "boolean",
                "description": "Whether to clear the buffer after reading.",
                "default": True,
            },
        },
        "required": ["session_id"],
    },
}

LIST_SESSIONS_TOOL: dict[str, Any] = {
    "name": "list_sessions",
    "description": "List all active terminal sessions.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_SESSION_INFO_TOOL: dict[str, Any] = {
    "name": "get_session_info",
    "description": "Return detailed information for the specified terminal session.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID (the serial port path), e.g. /dev/ttyUSB0 or COM1"
                ),
            },
        },
        "required": ["session_id"],
    },
}

CLEAR_BUFFER_TOOL: dict[str, Any] = {
    "name": "clear_buffer",
    "description": "Clear the output buffer of the specified terminal session.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": (
                    "Session ID (the serial port path), e.g. /dev/ttyUSB0 or COM1"
                ),
            },
        },
        "required": ["session_id"],
    },
}
