"""Type definitions module.

Defines data types related to serial port configuration and status.
"""

from dataclasses import dataclass
from enum import Enum


class Parity(str, Enum):
    """Parity bit enumeration."""

    NONE = "N"
    EVEN = "E"
    ODD = "O"
    MARK = "M"
    SPACE = "S"


class StopBits(float, Enum):
    """Stop bits enumeration."""

    ONE = 1
    ONE_POINT_FIVE = 1.5
    TWO = 2


class FlowControl(str, Enum):
    """Flow control enumeration."""

    NONE = "none"
    HARDWARE = "hardware"  # RTS/CTS
    SOFTWARE = "software"  # XON/XOFF


class LineEnding(str, Enum):
    """Terminal line ending enumeration."""

    CR = "\r"  # Carriage Return
    LF = "\n"  # Line Feed
    CRLF = "\r\n"  # Carriage Return + Line Feed


# Supported baud rates
SUPPORTED_BAUDRATES: tuple[int, ...] = (
    300,
    600,
    1200,
    2400,
    4800,
    9600,
    14400,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
)

# Supported data bits
SUPPORTED_BYTESIZES: tuple[int, ...] = (5, 6, 7, 8)

# Default configuration values
DEFAULT_BAUDRATE = 115200
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = Parity.NONE
DEFAULT_STOPBITS = StopBits.ONE
DEFAULT_FLOW_CONTROL = FlowControl.NONE
DEFAULT_TIMEOUT_MS = 1000
DEFAULT_WRITE_TIMEOUT_MS = 1000
DEFAULT_CONNECT_TIMEOUT_MS = 5000

# Default configuration for terminal sessions
DEFAULT_LINE_ENDING = LineEnding.CRLF
DEFAULT_BUFFER_SIZE = 65536  # 64KB
DEFAULT_LOCAL_ECHO = False


@dataclass
class SerialConfig:
    """Serial port configuration.

    Attributes:
        baudrate: Baud rate.
        bytesize: Data bits.
        parity: Parity bit.
        stopbits: Stop bits.
        flow_control: Flow control.
        read_timeout_ms: Read timeout (milliseconds).
        write_timeout_ms: Write timeout (milliseconds).
    """

    baudrate: int = DEFAULT_BAUDRATE
    bytesize: int = DEFAULT_BYTESIZE
    parity: Parity = DEFAULT_PARITY
    stopbits: StopBits = DEFAULT_STOPBITS
    flow_control: FlowControl = DEFAULT_FLOW_CONTROL
    read_timeout_ms: int = DEFAULT_TIMEOUT_MS
    write_timeout_ms: int = DEFAULT_WRITE_TIMEOUT_MS

    def to_dict(self) -> dict[str, int | str | float]:
        """Convert to dictionary form."""
        return {
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity.value,
            "stopbits": float(self.stopbits.value),
            "flow_control": self.flow_control.value,
            "read_timeout_ms": self.read_timeout_ms,
            "write_timeout_ms": self.write_timeout_ms,
        }


@dataclass
class PortInfo:
    """Serial port information.

    Attributes:
        port: Serial port path (e.g., /dev/ttyUSB0 or COM1).
        description: Serial port description.
        hwid: Hardware ID.
    """

    port: str
    description: str
    hwid: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary form."""
        return {
            "port": self.port,
            "description": self.description,
            "hwid": self.hwid,
        }


@dataclass
class PortStatus:
    """Serial port status.

    Attributes:
        port: Serial port path.
        is_open: Whether the port is open.
        config: Current configuration.
        connected: Physical connection state.
        reconnecting: Whether a reconnect is in progress.
    """

    port: str
    is_open: bool
    config: SerialConfig | None = None
    connected: bool = False
    reconnecting: bool = False

    def to_dict(self) -> dict[str, str | bool | dict[str, int | str | float] | None]:
        """Convert to dictionary form."""
        return {
            "port": self.port,
            "is_open": self.is_open,
            "config": self.config.to_dict() if self.config else None,
            "connected": self.connected,
            "reconnecting": self.reconnecting,
        }


@dataclass
class TerminalConfig:
    """Terminal session configuration.

    Attributes:
        line_ending: Line-ending type.
        local_echo: Whether to locally echo sent input.
        buffer_size: Output buffer size (bytes).
    """

    line_ending: LineEnding = DEFAULT_LINE_ENDING
    local_echo: bool = DEFAULT_LOCAL_ECHO
    buffer_size: int = DEFAULT_BUFFER_SIZE

    def to_dict(self) -> dict[str, str | bool | int]:
        """Convert to dictionary form."""
        return {
            "line_ending": self.line_ending.name,
            "local_echo": self.local_echo,
            "buffer_size": self.buffer_size,
        }


@dataclass
class SessionInfo:
    """Terminal session information.

    Attributes:
        session_id: Session ID (equal to the serial port path).
        port: Serial port path.
        config: Terminal configuration.
        buffer_size: Amount of data currently buffered (bytes).
        is_active: Whether the session is active.
        created_at: Creation timestamp.
    """

    session_id: str
    port: str
    config: TerminalConfig
    buffer_size: int
    is_active: bool
    created_at: float

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary form."""
        return {
            "session_id": self.session_id,
            "port": self.port,
            "config": self.config.to_dict(),
            "buffer_size": self.buffer_size,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
