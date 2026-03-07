import json
import socket
import time
import pytest
from unittest.mock import MagicMock, patch

from src.services.stream import TelemetryStreamServer


# ── Server Tests (real localhost sockets) ──

@pytest.fixture
def stream_server():
    """Start a TelemetryStreamServer on a high port for testing."""
    server = TelemetryStreamServer(host='localhost', port=19876)
    server.start()
    time.sleep(0.2)  # Let server thread start accepting
    yield server
    server.stop()


def _connect_client(port=19876, timeout=2.0):
    """Helper: create a connected client socket."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(timeout)
    client.connect(('localhost', port))
    time.sleep(0.1)  # Let server register the client
    return client


class TestTelemetryStreamServer:
    def test_starts_and_accepts_connections(self, stream_server):
        client = _connect_client()
        try:
            assert client is not None
            # Connection succeeded without exception
        finally:
            client.close()

    def test_broadcasts_json_to_client(self, stream_server, sample_telemetry_frame):
        client = _connect_client()
        try:
            stream_server.broadcast(sample_telemetry_frame)
            time.sleep(0.2)

            data = client.recv(65536).decode('utf-8')
            assert data.endswith('\n')
            parsed = json.loads(data.strip())
            assert parsed["frame_index"] == 0
            assert parsed["total_frames"] == 1000
            assert "1" in parsed["frame"]["drivers"]
            assert "44" in parsed["frame"]["drivers"]
        finally:
            client.close()

    def test_broadcasts_to_multiple_clients(self, stream_server, sample_telemetry_frame):
        client1 = _connect_client()
        client2 = _connect_client()
        try:
            stream_server.broadcast(sample_telemetry_frame)
            time.sleep(0.2)

            data1 = json.loads(client1.recv(65536).decode('utf-8').strip())
            data2 = json.loads(client2.recv(65536).decode('utf-8').strip())
            assert data1["frame_index"] == data2["frame_index"] == 0
        finally:
            client1.close()
            client2.close()

    def test_handles_disconnected_client(self, stream_server, sample_telemetry_frame):
        client1 = _connect_client()
        client2 = _connect_client()

        # Disconnect client1
        client1.close()
        time.sleep(0.2)

        # Broadcast should succeed — dead client removed, client2 gets data
        stream_server.broadcast(sample_telemetry_frame)
        time.sleep(0.2)

        try:
            data = json.loads(client2.recv(65536).decode('utf-8').strip())
            assert data["frame_index"] == 0
        finally:
            client2.close()

    def test_stop_closes_all(self, stream_server):
        client = _connect_client()
        stream_server.stop()
        time.sleep(0.2)

        assert stream_server.running is False
        assert len(stream_server.clients) == 0
        client.close()


# ── Client Parsing Tests (mocked sockets + signals) ──

class TestTelemetryStreamClientParsing:
    """Test the client's JSON parsing logic without running Qt event loop."""

    def _make_client(self):
        """Create a TelemetryStreamClient with mocked Qt internals."""
        # Patch PySide6 imports to avoid needing a display server
        with patch('src.services.stream.QThread.__init__', return_value=None):
            from src.services.stream import TelemetryStreamClient
            client = TelemetryStreamClient.__new__(TelemetryStreamClient)
            client.host = 'localhost'
            client.port = 19876
            client.socket = MagicMock()
            client.connected = True
            client.running = True
            client.data_received = MagicMock()
            client.connection_status = MagicMock()
            client.error_occurred = MagicMock()
            return client

    def test_parses_complete_json_message(self, sample_telemetry_frame):
        client = self._make_client()
        msg = json.dumps(sample_telemetry_frame).encode('utf-8') + b'\n'

        call_count = [0]
        def mock_recv(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return msg
            # Return empty to simulate server disconnect
            return b''

        client.socket.recv = mock_recv
        client._receive_data()

        client.data_received.emit.assert_called_once()
        parsed = client.data_received.emit.call_args[0][0]
        assert parsed["frame_index"] == 0

    def test_handles_chunked_data(self, sample_telemetry_frame):
        client = self._make_client()
        full_msg = json.dumps(sample_telemetry_frame).encode('utf-8') + b'\n'
        mid = len(full_msg) // 2
        chunk1 = full_msg[:mid]
        chunk2 = full_msg[mid:]

        call_count = [0]
        def mock_recv(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return chunk1
            elif call_count[0] == 2:
                return chunk2
            return b''

        client.socket.recv = mock_recv
        client._receive_data()

        client.data_received.emit.assert_called_once()

    def test_handles_multiple_messages(self, sample_telemetry_frame):
        client = self._make_client()
        msg = json.dumps(sample_telemetry_frame).encode('utf-8') + b'\n'
        two_msgs = msg + msg  # Two messages in one chunk

        call_count = [0]
        def mock_recv(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return two_msgs
            return b''

        client.socket.recv = mock_recv
        client._receive_data()

        assert client.data_received.emit.call_count == 2

    def test_handles_invalid_json(self):
        client = self._make_client()

        call_count = [0]
        def mock_recv(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return b'not-valid-json\n'
            return b''

        client.socket.recv = mock_recv
        client._receive_data()

        client.data_received.emit.assert_not_called()
        client.error_occurred.emit.assert_called()
        error_msg = client.error_occurred.emit.call_args[0][0]
        assert "JSON decode error" in error_msg

    def test_detects_server_disconnect(self):
        client = self._make_client()
        client.socket.recv = MagicMock(return_value=b'')

        client._receive_data()

        assert client.connected is False
