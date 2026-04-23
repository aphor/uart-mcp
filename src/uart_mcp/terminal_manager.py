"""Terminal session management module.

Provides creation, management, and data send/receive for terminal sessions.
Supports concurrent sessions, each with its own buffer.
"""

import logging
import threading
import time
from collections import deque
from typing import Any

from .errors import (
    InvalidLineEndingError,
    PortNotOpenError,
    SendCommandFailedError,
    SessionClosedError,
    SessionExistsError,
    SessionNotFoundError,
)
from .serial_manager import get_serial_manager
from .types import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_LINE_ENDING,
    DEFAULT_LOCAL_ECHO,
    LineEnding,
    SessionInfo,
    TerminalConfig,
)

logger = logging.getLogger(__name__)

# Background read interval (seconds)
READ_INTERVAL = 0.05  # 50ms


class TerminalSession:
    """Terminal session.

    Manages a terminal session for a single serial port, including its
    output buffer and background read thread.

    Attributes:
        session_id: Session ID (equal to the serial port path).
        port: Serial port path.
        config: Terminal configuration.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        port: str,
        line_ending: LineEnding = DEFAULT_LINE_ENDING,
        local_echo: bool = DEFAULT_LOCAL_ECHO,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
    ) -> None:
        """Initialize the terminal session.

        Args:
            port: Serial port path.
            line_ending: Line-ending type.
            local_echo: Whether to locally echo input.
            buffer_size: Output buffer size.
        """
        self.session_id = port
        self.port = port
        self.config = TerminalConfig(
            line_ending=line_ending,
            local_echo=local_echo,
            buffer_size=buffer_size,
        )
        self.created_at = time.time()

        # Output buffer (ring buffer implemented with a deque)
        self._buffer: deque[bytes] = deque()
        self._buffer_size = 0
        self._max_buffer_size = buffer_size
        self._buffer_lock = threading.Lock()

        # Background read thread control
        self._running = False
        self._read_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_active(self) -> bool:
        """Whether the session is active."""
        return self._running

    @property
    def buffer_length(self) -> int:
        """Current amount of buffered data (bytes)."""
        with self._buffer_lock:
            return self._buffer_size

    def start(self) -> None:
        """Start the background read thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"terminal-read-{self.port}",
        )
        self._read_thread.start()
        logger.info("Terminal session started: %s", self.session_id)

    def stop(self) -> None:
        """Stop the background read thread."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)

        logger.info("Terminal session stopped: %s", self.session_id)

    def _read_loop(self) -> None:
        """Background read loop."""
        manager = get_serial_manager()

        while not self._stop_event.is_set():
            try:
                # Read data from the serial port
                data = manager.read_data(self.port, timeout_ms=50)
                if data:
                    self._append_to_buffer(data)
            except Exception as e:
                # The port may have been closed or errored; stop reading
                if self._running:
                    logger.warning(
                        "Terminal read exception: %s - %s", self.session_id, e
                    )
                    self._running = False
                break

            # Brief sleep to avoid burning CPU
            self._stop_event.wait(READ_INTERVAL)

    def _append_to_buffer(self, data: bytes) -> None:
        """Append data to the buffer.

        If the buffer is full, the oldest chunks are discarded.

        Args:
            data: Bytes to append.
        """
        with self._buffer_lock:
            self._buffer.append(data)
            self._buffer_size += len(data)

            # Drop old data if over the size limit
            while self._buffer_size > self._max_buffer_size and self._buffer:
                old_data = self._buffer.popleft()
                self._buffer_size -= len(old_data)

    def read_output(self, clear: bool = True) -> bytes:
        """Read the contents of the output buffer.

        Args:
            clear: Whether to clear the buffer after reading.

        Returns:
            The data currently in the buffer.
        """
        with self._buffer_lock:
            if not self._buffer:
                return b""

            # Merge all chunks
            result = b"".join(self._buffer)

            if clear:
                self._buffer.clear()
                self._buffer_size = 0

            return result

    def clear_buffer(self) -> None:
        """Clear the output buffer."""
        with self._buffer_lock:
            self._buffer.clear()
            self._buffer_size = 0

    def send_command(self, command: str, add_line_ending: bool = True) -> int:
        """Send a command.

        Args:
            command: Command to send.
            add_line_ending: Whether to automatically append the line ending.

        Returns:
            Number of bytes written.

        Raises:
            SendCommandFailedError: Send failed.
        """
        manager = get_serial_manager()

        # Build payload
        data = command
        if add_line_ending:
            data += self.config.line_ending.value

        raw_data = data.encode("utf-8")

        try:
            bytes_written = manager.send_data(self.port, raw_data)

            # Local echo
            if self.config.local_echo:
                self._append_to_buffer(raw_data)

            logger.debug(
                "Terminal sent command: %s - %d bytes", self.session_id, bytes_written
            )
            return bytes_written
        except Exception as e:
            raise SendCommandFailedError(self.session_id, str(e)) from e

    def get_info(self) -> SessionInfo:
        """Return session information.

        Returns:
            Session information.
        """
        return SessionInfo(
            session_id=self.session_id,
            port=self.port,
            config=self.config,
            buffer_size=self.buffer_length,
            is_active=self.is_active,
            created_at=self.created_at,
        )


class TerminalManager:
    """Terminal manager.

    Manages all terminal sessions and exposes creation, close, and lookup
    operations. Uses a singleton pattern so only one manager exists globally.

    Attributes:
        _sessions: Session dict keyed by session ID (serial port path).
        _lock: Thread lock.
    """

    def __init__(self) -> None:
        """Initialize the terminal manager."""
        self._sessions: dict[str, TerminalSession] = {}
        self._lock = threading.RLock()

    def create_session(
        self,
        port: str,
        line_ending: str = DEFAULT_LINE_ENDING.name,
        local_echo: bool = DEFAULT_LOCAL_ECHO,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
    ) -> SessionInfo:
        """Create a terminal session.

        Args:
            port: Serial port path.
            line_ending: Line-ending type (CR/LF/CRLF).
            local_echo: Whether to locally echo input.
            buffer_size: Output buffer size.

        Returns:
            Session information.

        Raises:
            SessionExistsError: The session already exists.
            PortNotOpenError: The serial port is not open.
            InvalidLineEndingError: Invalid line-ending configuration.
        """
        # Validate line-ending configuration
        try:
            line_ending_enum = LineEnding[line_ending.upper()]
        except KeyError:
            raise InvalidLineEndingError(line_ending)

        # Check that the serial port is open
        manager = get_serial_manager()
        try:
            manager.get_status(port)
        except Exception:
            raise PortNotOpenError(port)

        with self._lock:
            # Check whether a session already exists
            if port in self._sessions:
                raise SessionExistsError(port)

            # Create the session
            session = TerminalSession(
                port=port,
                line_ending=line_ending_enum,
                local_echo=local_echo,
                buffer_size=buffer_size,
            )
            session.start()
            self._sessions[port] = session

            logger.info("Terminal session created: %s", port)
            return session.get_info()

    def close_session(self, session_id: str) -> dict[str, Any]:
        """Close a terminal session.

        Args:
            session_id: Session ID (serial port path).

        Returns:
            Operation result.

        Raises:
            SessionNotFoundError: Session not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)

            session = self._sessions.pop(session_id)
            session.stop()

            logger.info("Terminal session closed: %s", session_id)
            return {"success": True, "session_id": session_id}

    def get_session(self, session_id: str) -> TerminalSession:
        """Return a terminal session.

        Args:
            session_id: Session ID (serial port path).

        Returns:
            The terminal session.

        Raises:
            SessionNotFoundError: Session not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)
            return self._sessions[session_id]

    def send_command(
        self, session_id: str, command: str, add_line_ending: bool = True
    ) -> dict[str, Any]:
        """Send a command to a terminal.

        Args:
            session_id: Session ID (serial port path).
            command: Command to send.
            add_line_ending: Whether to automatically append the line ending.

        Returns:
            Send result.

        Raises:
            SessionNotFoundError: Session not found.
            SessionClosedError: Session is closed.
            SendCommandFailedError: Send failed.
        """
        session = self.get_session(session_id)

        if not session.is_active:
            raise SessionClosedError(session_id)

        bytes_written = session.send_command(command, add_line_ending)
        return {"success": True, "bytes_written": bytes_written}

    def read_output(self, session_id: str, clear: bool = True) -> dict[str, Any]:
        """Read output from a terminal.

        Args:
            session_id: Session ID (serial port path).
            clear: Whether to clear the buffer after reading.

        Returns:
            Output content.

        Raises:
            SessionNotFoundError: Session not found.
        """
        session = self.get_session(session_id)
        data = session.read_output(clear)

        # Decode to string, replacing undecodable bytes
        text = data.decode("utf-8", errors="replace")

        return {
            "data": text,
            "bytes_read": len(data),
        }

    def clear_buffer(self, session_id: str) -> dict[str, Any]:
        """Clear the terminal buffer.

        Args:
            session_id: Session ID (serial port path).

        Returns:
            Operation result.

        Raises:
            SessionNotFoundError: Session not found.
        """
        session = self.get_session(session_id)
        session.clear_buffer()
        return {"success": True, "session_id": session_id}

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all terminal sessions.

        Returns:
            List of session info dicts.
        """
        with self._lock:
            return [session.get_info().to_dict() for session in self._sessions.values()]

    def get_session_info(self, session_id: str) -> dict[str, Any]:
        """Return detailed session information.

        Args:
            session_id: Session ID (serial port path).

        Returns:
            Session information.

        Raises:
            SessionNotFoundError: Session not found.
        """
        session = self.get_session(session_id)
        return session.get_info().to_dict()

    def shutdown(self) -> None:
        """Shut down the manager.

        Stops every session.
        """
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                try:
                    session.stop()
                    logger.debug("Closed terminal session: %s", session_id)
                except Exception as e:
                    logger.warning(
                        "Failed to close terminal session: %s - %s", session_id, e
                    )
            self._sessions.clear()

        logger.info("Terminal manager has been shut down")


# Global terminal manager instance
_terminal_manager: TerminalManager | None = None


def get_terminal_manager() -> TerminalManager:
    """Return the terminal manager singleton.

    Returns:
        Terminal manager instance.
    """
    global _terminal_manager
    if _terminal_manager is None:
        _terminal_manager = TerminalManager()
    return _terminal_manager
