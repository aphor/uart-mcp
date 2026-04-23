"""Integration tests using a real serial device with loopback.

These tests exercise all MCP tool functions and require a physically connected
serial device with TX and RX bridged for loopback.
Default test port: /dev/ttyUSB0

Usage:
    pytest tests/test_integration_real_port.py -v
    or run directly:
    python tests/test_integration_real_port.py
"""

import base64
import sys
import time
from typing import Any

# Test configuration
TEST_PORT = "/dev/ttyUSB0"
TEST_BAUDRATE = 115200


def print_result(test_name: str, success: bool, result: Any = None) -> None:
    """Print a test result."""
    status = "PASS" if success else "FAIL"
    print(f"  {status}: {test_name}")
    if result and not success:
        print(f"    detail: {result}")


def test_list_ports() -> None:
    """Test 1: list all available serial ports."""
    from uart_mcp.tools.list_ports import list_ports

    try:
        ports = list_ports()
        found = any(p["port"] == TEST_PORT for p in ports)
        print_result("list_ports - list ports", found, ports)
        if found:
            print(f"    Found target port: {TEST_PORT}")
        assert found, f"Target port {TEST_PORT} not found"
    except Exception as e:
        print_result("list_ports - list ports", False, str(e))
        assert False, str(e)


def test_open_port() -> None:
    """Test 2: open a serial port."""
    from uart_mcp.tools.port_ops import open_port

    try:
        result = open_port(
            port=TEST_PORT,
            baudrate=TEST_BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1.0,
        )
        success = result.get("is_open", False)
        print_result("open_port - open port", success, result)
        assert success, "Failed to open port"
    except Exception as e:
        print_result("open_port - open port", False, str(e))
        assert False, str(e)


def test_get_status() -> None:
    """Test 3: fetch serial port status."""
    from uart_mcp.tools.port_ops import get_status

    try:
        result = get_status(port=TEST_PORT)
        config = result.get("config", {})
        success = result.get("is_open", False) and config.get("baudrate") == TEST_BAUDRATE
        print_result("get_status - get status", success, result)
        assert success, "Failed to get status"
    except Exception as e:
        print_result("get_status - get status", False, str(e))
        assert False, str(e)


def test_set_config() -> None:
    """Test 4: modify serial port config (hot update)."""
    from uart_mcp.tools.port_ops import set_config

    try:
        # Change the baud rate
        new_baudrate = 9600
        result = set_config(port=TEST_PORT, baudrate=new_baudrate)
        config = result.get("config", {})
        success = config.get("baudrate") == new_baudrate
        print_result("set_config - modify config", success, result)

        # Restore the original config
        set_config(port=TEST_PORT, baudrate=TEST_BAUDRATE)
        assert success, "Failed to modify config"
    except Exception as e:
        print_result("set_config - modify config", False, str(e))
        assert False, str(e)


def test_send_receive_text() -> None:
    """Test 5: send and receive text data (loopback test)."""
    from uart_mcp.tools.data_ops import read_data, send_data

    try:
        test_message = "Hello UART loopback!"

        # Send data
        send_result = send_data(port=TEST_PORT, data=test_message, is_binary=False)
        if not send_result.get("success"):
            print_result("send_data - send text", False, send_result)
            assert False, "Failed to send text"

        # Wait for loopback
        time.sleep(0.1)

        # Read data
        read_result = read_data(port=TEST_PORT, is_binary=False)
        received = read_result.get("data", "")

        success = test_message in received
        print_result(
            "send/read_data - text loopback",
            success,
            f"sent: {test_message}, received: {received}"
        )
        assert success, "Text loopback test failed"
    except Exception as e:
        print_result("send/read_data - text loopback", False, str(e))
        assert False, str(e)


def test_send_receive_binary() -> None:
    """Test 6: send and receive binary data (loopback test)."""
    from uart_mcp.tools.data_ops import read_data, send_data

    try:
        # Prepare binary data
        raw_data = bytes([0x01, 0x02, 0x03, 0xFE, 0xFF])
        b64_data = base64.b64encode(raw_data).decode("ascii")

        # Send binary data
        send_result = send_data(port=TEST_PORT, data=b64_data, is_binary=True)
        if not send_result.get("success"):
            print_result("send_data - send binary", False, send_result)
            assert False, "Failed to send binary"

        # Wait for loopback
        time.sleep(0.1)

        # Read binary data
        read_result = read_data(port=TEST_PORT, is_binary=True)
        received_b64 = read_result.get("data", "")
        received_raw = base64.b64decode(received_b64) if received_b64 else b""

        success = raw_data == received_raw
        print_result(
            "send/read_data - binary loopback",
            success,
            f"sent: {raw_data.hex()}, received: {received_raw.hex()}"
        )
        assert success, "Binary loopback test failed"
    except Exception as e:
        print_result("send/read_data - binary loopback", False, str(e))
        assert False, str(e)


def test_create_session() -> None:
    """Test 7: create a terminal session."""
    from uart_mcp.tools.terminal import create_session

    try:
        result = create_session(
            port=TEST_PORT,
            line_ending="CRLF",
            local_echo=False,
        )
        success = result.get("session_id") == TEST_PORT
        print_result("create_session - create session", success, result)
        assert success, "Failed to create session"
    except Exception as e:
        print_result("create_session - create session", False, str(e))
        assert False, str(e)


def test_list_sessions() -> None:
    """Test 8: list all sessions."""
    from uart_mcp.tools.terminal import list_sessions

    try:
        result = list_sessions()
        sessions = result.get("sessions", [])
        session_ids = [
            s.get("session_id") if isinstance(s, dict) else s for s in sessions
        ]
        success = TEST_PORT in session_ids
        print_result("list_sessions - list sessions", success, result)
        assert success, "Failed to list sessions"
    except Exception as e:
        print_result("list_sessions - list sessions", False, str(e))
        assert False, str(e)


def test_get_session_info() -> None:
    """Test 9: get session info."""
    from uart_mcp.tools.terminal import get_session_info

    try:
        result = get_session_info(session_id=TEST_PORT)
        success = result.get("session_id") == TEST_PORT
        print_result("get_session_info - session info", success, result)
        assert success, "Failed to get session info"
    except Exception as e:
        print_result("get_session_info - session info", False, str(e))
        assert False, str(e)


def test_send_command_read_output() -> None:
    """Test 10: send a command and read the output (loopback test)."""
    from uart_mcp.tools.terminal import read_output, send_command

    try:
        test_cmd = "AT"

        # Clear the buffer first
        from uart_mcp.tools.terminal import clear_buffer
        clear_buffer(session_id=TEST_PORT)
        time.sleep(0.1)

        # Send the command
        send_result = send_command(
            session_id=TEST_PORT,
            command=test_cmd,
            add_line_ending=True,
        )
        if not send_result.get("success"):
            print_result("send_command - send command", False, send_result)
            assert False, "Failed to send command"

        # Poll up to 2 seconds for the loopback data to arrive
        output = ""
        for _ in range(20):  # 20 x 100 ms = 2 s
            time.sleep(0.1)
            read_result = read_output(session_id=TEST_PORT, clear=False)
            output = read_result.get("data", "")
            if test_cmd in output:
                break

        # Clear the buffer
        clear_buffer(session_id=TEST_PORT)

        success = test_cmd in output
        print_result(
            "send/read_output - command loopback",
            success,
            f"sent: {test_cmd}, output: {repr(output)}"
        )
        assert success, "Command loopback test failed"
    except Exception as e:
        print_result("send/read_output - command loopback", False, str(e))
        assert False, str(e)


def test_clear_buffer() -> None:
    """Test 11: clear the buffer."""
    from uart_mcp.tools.terminal import clear_buffer, read_output

    try:
        result = clear_buffer(session_id=TEST_PORT)
        success = result.get("success", False)
        print_result("clear_buffer - clear buffer", success, result)

        # Verify the buffer is empty
        read_result = read_output(session_id=TEST_PORT, clear=False)
        empty = len(read_result.get("data", "")) == 0
        print_result("clear_buffer - verify empty", empty, read_result)

        assert success and empty, "Failed to clear buffer"
    except Exception as e:
        print_result("clear_buffer - clear buffer", False, str(e))
        assert False, str(e)


def test_close_session() -> None:
    """Test 12: close a terminal session."""
    from uart_mcp.tools.terminal import close_session

    try:
        result = close_session(session_id=TEST_PORT)
        success = result.get("success", False)
        print_result("close_session - close session", success, result)
        assert success
    except Exception as e:
        print_result("close_session - close session", False, str(e))
        assert False, str(e)


def test_close_port() -> None:
    """Test 13: close the serial port."""
    from uart_mcp.tools.port_ops import close_port

    try:
        result = close_port(port=TEST_PORT)
        success = result.get("success", False)
        print_result("close_port - close port", success, result)
        assert success
    except Exception as e:
        print_result("close_port - close port", False, str(e))
        assert False, str(e)


def run_all_tests() -> None:
    """Run all integration tests (standalone script mode)."""
    print("=" * 60)
    print("UART MCP Integration Tests - Real Serial Loopback")
    print(f"Test port: {TEST_PORT}")
    print(f"Baud rate: {TEST_BAUDRATE}")
    print("=" * 60)

    tests = [
        ("list_ports", test_list_ports),
        ("open_port", test_open_port),
        ("get_status", test_get_status),
        ("set_config", test_set_config),
        ("send_receive_text", test_send_receive_text),
        ("send_receive_binary", test_send_receive_binary),
        ("create_session", test_create_session),
        ("list_sessions", test_list_sessions),
        ("get_session_info", test_get_session_info),
        ("send_command_read_output", test_send_command_read_output),
        ("clear_buffer", test_clear_buffer),
        ("close_session", test_close_session),
        ("close_port", test_close_port),
    ]

    results: dict[str, bool] = {}

    for name, test_func in tests:
        try:
            test_func()
            results[name] = True
        except AssertionError:
            results[name] = False
        except Exception as e:
            print(f"  Test {name} raised an exception: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {status}  {name}")

    print("-" * 40)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed — see details above.")


if __name__ == "__main__":
    # Allow overriding port and baud rate from the command line
    if len(sys.argv) > 1:
        TEST_PORT = sys.argv[1]
    if len(sys.argv) > 2:
        TEST_BAUDRATE = int(sys.argv[2])

    run_all_tests()
