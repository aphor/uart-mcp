"""list_ports tool implementation.

Enumerates every serial port device available on the system.
"""

from typing import Any

from ..serial_manager import get_serial_manager


def list_ports() -> list[dict[str, str]]:
    """List all available serial port devices.

    Returns every serial port device available on the system, filtered by
    the blacklist.

    Returns:
        List of serial port info dicts, each with port, description, and hwid fields.
    """
    manager = get_serial_manager()
    ports = manager.list_ports()
    return [p.to_dict() for p in ports]


# Tool definition (used for MCP registration)
LIST_PORTS_TOOL: dict[str, Any] = {
    "name": "list_ports",
    "description": (
        "List all available serial port devices. Returns the device path, "
        "description, and hardware ID for each."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}
