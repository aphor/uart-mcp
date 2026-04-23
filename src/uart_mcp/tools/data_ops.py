"""Data communication tool implementation.

Provides serial-port send/receive functionality for both text and binary modes.
"""

import base64
from typing import Any

from ..errors import InvalidParamError
from ..serial_manager import get_serial_manager


def send_data(
    port: str,
    data: str,
    is_binary: bool = False,
) -> dict[str, Any]:
    """Send data to a serial port.

    Args:
        port: Serial port path.
        data: Data to send (UTF-8 string for text mode, Base64-encoded for binary mode).
        is_binary: Whether to use binary mode.

    Returns:
        Send result, including the number of bytes written.
    """
    manager = get_serial_manager()

    # Decode input
    if is_binary:
        try:
            raw_data = base64.b64decode(data)
        except Exception as e:
            raise InvalidParamError("data", data, f"Base64 decode failed: {e}")
    else:
        raw_data = data.encode("utf-8")

    bytes_written = manager.send_data(port, raw_data)
    return {"success": True, "bytes_written": bytes_written}


def read_data(
    port: str,
    size: int | None = None,
    timeout_ms: int | None = None,
    is_binary: bool = False,
) -> dict[str, Any]:
    """Read data from a serial port.

    Args:
        port: Serial port path.
        size: Number of bytes to read; None reads all available data.
        timeout_ms: Read timeout in ms; None uses the port's configured timeout.
        is_binary: Whether to use binary mode.

    Returns:
        Read result containing the data and byte count.
    """
    manager = get_serial_manager()
    raw_data = manager.read_data(port, size, timeout_ms)

    # Encode output
    if is_binary:
        result_data = base64.b64encode(raw_data).decode("ascii")
    else:
        result_data = raw_data.decode("utf-8", errors="replace")

    return {"data": result_data, "bytes_read": len(raw_data)}


# Tool definitions (used for MCP registration)
SEND_DATA_TOOL: dict[str, Any] = {
    "name": "send_data",
    "description": (
        "Send data to an open serial port. Supports text and binary modes."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path, e.g. /dev/ttyUSB0 or COM1",
            },
            "data": {
                "type": "string",
                "description": "Data to send (UTF-8 for text, Base64 for binary)",
            },
            "is_binary": {
                "type": "boolean",
                "description": (
                    "Whether to use binary mode. When true, data must be Base64-encoded."
                ),
                "default": False,
            },
        },
        "required": ["port", "data"],
    },
}

READ_DATA_TOOL: dict[str, Any] = {
    "name": "read_data",
    "description": (
        "Read data from an open serial port. Supports text and binary modes."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path, e.g. /dev/ttyUSB0 or COM1",
            },
            "size": {
                "type": "integer",
                "description": (
                    "Number of bytes to read; if omitted, reads all available data."
                ),
            },
            "timeout_ms": {
                "type": "integer",
                "description": (
                    "Read timeout in milliseconds; if omitted, uses the port's "
                    "configured timeout."
                ),
            },
            "is_binary": {
                "type": "boolean",
                "description": (
                    "Whether to use binary mode. When true, data is returned as Base64."
                ),
                "default": False,
            },
        },
        "required": ["port"],
    },
}
