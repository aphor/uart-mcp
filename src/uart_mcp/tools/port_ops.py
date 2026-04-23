"""Serial port operation tools.

Provides functions for opening, closing, and configuring serial ports.
"""

from typing import Any

from ..serial_manager import get_serial_manager
from ..types import (
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FLOW_CONTROL,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_WRITE_TIMEOUT_MS,
    SUPPORTED_BAUDRATES,
    SUPPORTED_BYTESIZES,
    FlowControl,
    Parity,
    StopBits,
)


def open_port(
    port: str,
    baudrate: int = DEFAULT_BAUDRATE,
    bytesize: int = DEFAULT_BYTESIZE,
    parity: str = DEFAULT_PARITY.value,
    stopbits: float = float(DEFAULT_STOPBITS.value),
    flow_control: str = DEFAULT_FLOW_CONTROL.value,
    read_timeout_ms: int = DEFAULT_TIMEOUT_MS,
    write_timeout_ms: int = DEFAULT_WRITE_TIMEOUT_MS,
    auto_reconnect: bool = True,
) -> dict[str, Any]:
    """Open a serial port.

    Args:
        port: Serial port path (e.g., /dev/ttyUSB0 or COM1).
        baudrate: Baud rate, default 9600.
        bytesize: Data bits, default 8.
        parity: Parity bit, default N (no parity).
        stopbits: Stop bits, default 1.
        flow_control: Flow control, default none.
        read_timeout_ms: Read timeout in ms, default 1000.
        write_timeout_ms: Write timeout in ms, default 1000.
        auto_reconnect: Whether to enable auto-reconnect, default True.

    Returns:
        Serial port status information.
    """
    manager = get_serial_manager()
    status = manager.open_port(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
        flow_control=flow_control,
        read_timeout_ms=read_timeout_ms,
        write_timeout_ms=write_timeout_ms,
        auto_reconnect=auto_reconnect,
    )
    return status.to_dict()


def close_port(port: str) -> dict[str, Any]:
    """Close a serial port.

    Args:
        port: Serial port path.

    Returns:
        Operation result.
    """
    manager = get_serial_manager()
    return manager.close_port(port)


def set_config(
    port: str,
    baudrate: int | None = None,
    bytesize: int | None = None,
    parity: str | None = None,
    stopbits: float | None = None,
    flow_control: str | None = None,
    read_timeout_ms: int | None = None,
    write_timeout_ms: int | None = None,
) -> dict[str, Any]:
    """Update the serial port configuration (hot update).

    Args:
        port: Serial port path.
        baudrate: Baud rate (optional).
        bytesize: Data bits (optional).
        parity: Parity bit (optional).
        stopbits: Stop bits (optional).
        flow_control: Flow control (optional).
        read_timeout_ms: Read timeout (optional).
        write_timeout_ms: Write timeout (optional).

    Returns:
        Updated serial port status.
    """
    manager = get_serial_manager()
    status = manager.set_config(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
        flow_control=flow_control,
        read_timeout_ms=read_timeout_ms,
        write_timeout_ms=write_timeout_ms,
    )
    return status.to_dict()


def get_status(port: str) -> dict[str, Any]:
    """Return the serial port status.

    Args:
        port: Serial port path.

    Returns:
        Serial port status information.
    """
    manager = get_serial_manager()
    status = manager.get_status(port)
    return status.to_dict()


# Tool definitions (used for MCP registration)
OPEN_PORT_TOOL: dict[str, Any] = {
    "name": "open_port",
    "description": (
        "Open the specified serial port, with optional custom configuration."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path, e.g. /dev/ttyUSB0 or COM1",
            },
            "baudrate": {
                "type": "integer",
                "description": f"Baud rate. Supported values: {list(SUPPORTED_BAUDRATES)}",
                "default": DEFAULT_BAUDRATE,
            },
            "bytesize": {
                "type": "integer",
                "description": f"Data bits. Supported values: {list(SUPPORTED_BYTESIZES)}",
                "default": DEFAULT_BYTESIZE,
            },
            "parity": {
                "type": "string",
                "description": f"Parity bit. Supported values: {[p.value for p in Parity]}",
                "default": DEFAULT_PARITY.value,
            },
            "stopbits": {
                "type": "number",
                "description": f"Stop bits. Supported values: {[s.value for s in StopBits]}",
                "default": float(DEFAULT_STOPBITS.value),
            },
            "flow_control": {
                "type": "string",
                "description": f"Flow control. Supported values: {[f.value for f in FlowControl]}",
                "default": DEFAULT_FLOW_CONTROL.value,
            },
            "read_timeout_ms": {
                "type": "integer",
                "description": "Read timeout in ms, range 0-60000",
                "default": DEFAULT_TIMEOUT_MS,
            },
            "write_timeout_ms": {
                "type": "integer",
                "description": "Write timeout in ms, range 0-60000",
                "default": DEFAULT_WRITE_TIMEOUT_MS,
            },
            "auto_reconnect": {
                "type": "boolean",
                "description": "Whether to enable auto-reconnect",
                "default": True,
            },
        },
        "required": ["port"],
    },
}

CLOSE_PORT_TOOL: dict[str, Any] = {
    "name": "close_port",
    "description": "Close the specified serial port connection.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path",
            },
        },
        "required": ["port"],
    },
}

SET_CONFIG_TOOL: dict[str, Any] = {
    "name": "set_config",
    "description": (
        "Update the configuration of an open serial port (hot update; no "
        "close/reopen required)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path",
            },
            "baudrate": {
                "type": "integer",
                "description": f"Baud rate. Supported values: {list(SUPPORTED_BAUDRATES)}",
            },
            "bytesize": {
                "type": "integer",
                "description": f"Data bits. Supported values: {list(SUPPORTED_BYTESIZES)}",
            },
            "parity": {
                "type": "string",
                "description": f"Parity bit. Supported values: {[p.value for p in Parity]}",
            },
            "stopbits": {
                "type": "number",
                "description": f"Stop bits. Supported values: {[s.value for s in StopBits]}",
            },
            "flow_control": {
                "type": "string",
                "description": f"Flow control. Supported values: {[f.value for f in FlowControl]}",
            },
            "read_timeout_ms": {
                "type": "integer",
                "description": "Read timeout in ms, range 0-60000",
            },
            "write_timeout_ms": {
                "type": "integer",
                "description": "Write timeout in ms, range 0-60000",
            },
        },
        "required": ["port"],
    },
}

GET_STATUS_TOOL: dict[str, Any] = {
    "name": "get_status",
    "description": (
        "Return the current status and configuration of an open serial port."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "Serial port path",
            },
        },
        "required": ["port"],
    },
}
