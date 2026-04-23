"""Error code definitions module.

Defines all error codes and exception classes related to serial port operations.
"""

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """Error code enumeration.

    Defines all error codes that serial port operations may return.
    """

    # Serial port error codes (1001-1999)
    PORT_NOT_FOUND = 1001  # Serial port does not exist
    PORT_BUSY = 1002  # Serial port is in use
    PORT_OPEN_FAILED = 1003  # Failed to open serial port
    PORT_CLOSED = 1004  # Serial port is closed
    INVALID_PARAM = 1005  # Invalid parameter
    READ_TIMEOUT = 1006  # Read timed out
    WRITE_FAILED = 1007  # Write failed
    PERMISSION_DENIED = 1008  # Insufficient permissions
    PORT_BLACKLISTED = 1009  # Serial port is blacklisted

    # Terminal session error codes (2001-2006)
    SESSION_EXISTS = 2001  # Session already exists
    SESSION_NOT_FOUND = 2002  # Session not found
    PORT_NOT_OPEN = 2003  # Serial port is not open
    SESSION_CLOSED = 2004  # Session is closed
    SEND_COMMAND_FAILED = 2005  # Failed to send command
    INVALID_LINE_ENDING = 2006  # Invalid line-ending configuration


# Human-readable message for each error code
ERROR_MESSAGES: dict[ErrorCode, str] = {
    # Serial port
    ErrorCode.PORT_NOT_FOUND: "Serial port not found",
    ErrorCode.PORT_BUSY: "Serial port is in use",
    ErrorCode.PORT_OPEN_FAILED: "Failed to open serial port",
    ErrorCode.PORT_CLOSED: "Serial port is closed",
    ErrorCode.INVALID_PARAM: "Invalid parameter",
    ErrorCode.READ_TIMEOUT: "Read timed out",
    ErrorCode.WRITE_FAILED: "Write failed",
    ErrorCode.PERMISSION_DENIED: "Permission denied",
    ErrorCode.PORT_BLACKLISTED: "Serial port is blacklisted",
    # Terminal session
    ErrorCode.SESSION_EXISTS: "Session already exists",
    ErrorCode.SESSION_NOT_FOUND: "Session not found",
    ErrorCode.PORT_NOT_OPEN: "Serial port is not open",
    ErrorCode.SESSION_CLOSED: "Session is closed",
    ErrorCode.SEND_COMMAND_FAILED: "Failed to send command",
    ErrorCode.INVALID_LINE_ENDING: "Invalid line-ending configuration",
}


class SerialError(Exception):
    """Base exception for serial port operations.

    All serial-port-related exceptions inherit from this class.

    Attributes:
        code: Error code.
        message: Error message.
        detail: Additional error detail.
    """

    def __init__(
        self, code: ErrorCode, detail: str | None = None, **kwargs: Any
    ) -> None:
        """Initialize a serial port exception.

        Args:
            code: Error code.
            detail: Additional detail appended after the default message.
            **kwargs: Additional arguments used to format the message.
        """
        self.code = code
        base_message = ERROR_MESSAGES.get(code, "Unknown error")
        self.message = f"{base_message}: {detail}" if detail else base_message
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary form.

        Returns:
            Dict containing the error code and message.
        """
        return {"error": {"code": int(self.code), "message": self.message}}


class PortNotFoundError(SerialError):
    """Raised when the serial port does not exist."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_NOT_FOUND, port)


class PortBusyError(SerialError):
    """Raised when the serial port is already in use."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_BUSY, port)


class PortOpenFailedError(SerialError):
    """Raised when opening the serial port fails."""

    def __init__(self, port: str, reason: str | None = None) -> None:
        detail = f"{port}" if not reason else f"{port} - {reason}"
        super().__init__(ErrorCode.PORT_OPEN_FAILED, detail)


class PortClosedError(SerialError):
    """Raised when the serial port is already closed."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_CLOSED, port)


class InvalidParamError(SerialError):
    """Raised when a parameter value is invalid."""

    def __init__(self, param: str, value: Any, reason: str | None = None) -> None:
        detail = f"{param}={value}"
        if reason:
            detail = f"{detail} ({reason})"
        super().__init__(ErrorCode.INVALID_PARAM, detail)


class PermissionDeniedError(SerialError):
    """Raised when permissions are insufficient to access the port."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PERMISSION_DENIED, port)


class PortBlacklistedError(SerialError):
    """Raised when the serial port is on the blacklist."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_BLACKLISTED, port)


class WriteFailedError(SerialError):
    """Raised when writing to the serial port fails."""

    def __init__(self, port: str, reason: str | None = None) -> None:
        detail = f"{port}" if not reason else f"{port} - {reason}"
        super().__init__(ErrorCode.WRITE_FAILED, detail)


# Terminal session exception classes


class TerminalError(SerialError):
    """Base exception for terminal session operations."""

    pass


class SessionExistsError(TerminalError):
    """Raised when the session already exists."""

    def __init__(self, session_id: str) -> None:
        super().__init__(ErrorCode.SESSION_EXISTS, session_id)


class SessionNotFoundError(TerminalError):
    """Raised when the session cannot be found."""

    def __init__(self, session_id: str) -> None:
        super().__init__(ErrorCode.SESSION_NOT_FOUND, session_id)


class PortNotOpenError(TerminalError):
    """Raised when the serial port is not open."""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_NOT_OPEN, port)


class SessionClosedError(TerminalError):
    """Raised when the session is already closed."""

    def __init__(self, session_id: str) -> None:
        super().__init__(ErrorCode.SESSION_CLOSED, session_id)


class SendCommandFailedError(TerminalError):
    """Raised when sending a command fails."""

    def __init__(self, session_id: str, reason: str | None = None) -> None:
        detail = f"{session_id}" if not reason else f"{session_id} - {reason}"
        super().__init__(ErrorCode.SEND_COMMAND_FAILED, detail)


class InvalidLineEndingError(TerminalError):
    """Raised when the line-ending configuration is invalid."""

    def __init__(self, value: str) -> None:
        super().__init__(ErrorCode.INVALID_LINE_ENDING, value)
