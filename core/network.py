"""Network module - TCP and UDP with disconnect handling, ping, reconnect."""

import socket
import threading
import pickle
import struct
import time


def get_local_ip():
    """Get local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class NetworkMessage:
    """Wrapper for network messages."""

    def __init__(self, msg_type, data=None):
        self.msg_type = msg_type
        self.data = data or {}
        self.timestamp = time.time()


# === Internal message types (not forwarded to game) ===
_INTERNAL_TYPES = {"_ping", "_pong", "_reconnect", "_reconnect_ack", "_disconnect"}


class TCPServer:
    """TCP server with ping/timeout/reconnect support."""

    PING_INTERVAL = 2.0        # Send ping every 2s
    TIMEOUT = 8.0              # Consider disconnected after 8s no response
    RECONNECT_WINDOW = 30.0    # Allow reconnect within 30s

    def __init__(self, port=5555):
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.connected = False
        self.message_queue = []
        self._lock = threading.Lock()
        self.error = None

        # Callbacks
        self.on_connect = None
        self.on_disconnect = None
        self.on_reconnect = None

        # Ping/timeout tracking
        self.last_ping_sent = 0
        self.last_pong_received = 0
        self.ping_ms = 0
        self._ping_send_time = 0

        # Disconnect state
        self.disconnect_time = None
        self.peer_disconnected = False
        self._accepting_reconnect = False
        self._client_addr = None

    def start(self):
        """Start server in background thread."""
        self.running = True
        self.error = None
        self.disconnect_time = None
        self.peer_disconnected = False
        thread = threading.Thread(target=self._server_loop, daemon=True)
        thread.start()

    def _server_loop(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(1)

            while self.running:
                try:
                    client, addr = self.server_socket.accept()
                    self.client_socket = client
                    self._client_addr = addr
                    self.connected = True
                    self.peer_disconnected = False
                    self.disconnect_time = None
                    self.last_pong_received = time.time()
                    self.last_ping_sent = time.time()

                    if self._accepting_reconnect:
                        self._accepting_reconnect = False
                        _send_msg(client, NetworkMessage("_reconnect_ack"))
                        if self.on_reconnect:
                            self.on_reconnect(addr)
                    else:
                        if self.on_connect:
                            self.on_connect(addr)

                    self._receive_loop(client)

                    # After receive loop ends — client disconnected
                    self._handle_client_disconnect()

                except socket.timeout:
                    # Check if we're waiting for reconnect and it timed out
                    if (self._accepting_reconnect and self.disconnect_time and
                            time.time() - self.disconnect_time > self.RECONNECT_WINDOW):
                        self._accepting_reconnect = False
                        self.peer_disconnected = True
                        with self._lock:
                            self.message_queue.append(
                                NetworkMessage("_disconnect", {"reason": "reconnect_timeout"})
                            )
                    continue
                except OSError:
                    break
        except Exception as e:
            self.error = str(e)
        finally:
            self.stop()

    def _handle_client_disconnect(self):
        """Handle when client connection drops."""
        self.connected = False
        self.disconnect_time = time.time()
        self._accepting_reconnect = True
        self.peer_disconnected = True

        if self.on_disconnect:
            self.on_disconnect()

        with self._lock:
            self.message_queue.append(
                NetworkMessage("_disconnect", {"reason": "connection_lost",
                                                "reconnect_possible": True})
            )

    def _receive_loop(self, sock):
        sock.settimeout(0.5)
        while self.running and self.connected:
            try:
                data = _recv_msg(sock)
                if data is None:
                    self.connected = False
                    break

                # Handle internal messages
                if isinstance(data, NetworkMessage):
                    if data.msg_type == "_pong":
                        self.last_pong_received = time.time()
                        self.ping_ms = int((time.time() - self._ping_send_time) * 1000)
                        continue
                    elif data.msg_type == "_ping":
                        # Reply with pong
                        try:
                            _send_msg(sock, NetworkMessage("_pong"))
                        except Exception:
                            pass
                        continue
                    elif data.msg_type == "_disconnect":
                        self.connected = False
                        break

                self.last_pong_received = time.time()  # Any message counts
                with self._lock:
                    self.message_queue.append(data)

            except socket.timeout:
                # Check if we should send ping
                now = time.time()
                if now - self.last_ping_sent >= self.PING_INTERVAL:
                    try:
                        self._ping_send_time = now
                        _send_msg(sock, NetworkMessage("_ping"))
                        self.last_ping_sent = now
                    except Exception:
                        self.connected = False
                        break

                # Check timeout
                if now - self.last_pong_received > self.TIMEOUT:
                    self.connected = False
                    break
                continue
            except Exception:
                self.connected = False
                break

    def send(self, msg):
        """Send a message to client."""
        if self.client_socket and self.connected:
            try:
                _send_msg(self.client_socket, msg)
            except Exception:
                self.connected = False

    def get_messages(self):
        """Get and clear message queue (including disconnect notifications)."""
        with self._lock:
            msgs = self.message_queue[:]
            self.message_queue.clear()
        return msgs

    def is_peer_disconnected(self):
        """Check if peer is currently disconnected."""
        return self.peer_disconnected

    def get_disconnect_elapsed(self):
        """How long since disconnect (seconds)."""
        if self.disconnect_time:
            return time.time() - self.disconnect_time
        return 0

    def get_reconnect_remaining(self):
        """Seconds remaining for reconnect window."""
        if self.disconnect_time:
            remaining = self.RECONNECT_WINDOW - (time.time() - self.disconnect_time)
            return max(0, remaining)
        return 0

    def stop(self):
        """Stop server and send graceful disconnect."""
        self.running = False
        if self.client_socket and self.connected:
            try:
                _send_msg(self.client_socket, NetworkMessage("_disconnect",
                          {"reason": "server_closed"}))
            except Exception:
                pass
        self.connected = False
        self.peer_disconnected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass


class TCPClient:
    """TCP client with reconnect support."""

    PING_INTERVAL = 2.0
    TIMEOUT = 8.0
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 2.0

    def __init__(self):
        self.socket = None
        self.connected = False
        self.message_queue = []
        self._lock = threading.Lock()
        self.running = False
        self.error = None

        # Connection info (for reconnect)
        self._host = None
        self._port = None

        # Ping
        self.last_ping_sent = 0
        self.last_pong_received = 0
        self.ping_ms = 0
        self._ping_send_time = 0

        # Reconnect state
        self.reconnecting = False
        self.reconnect_attempt = 0
        self.peer_disconnected = False
        self.disconnect_time = None

        # Callbacks
        self.on_disconnect = None
        self.on_reconnect = None

    def connect(self, host, port=5555):
        """Connect to server in background."""
        self._host = host
        self._port = port
        self.running = True
        self.error = None
        self.reconnecting = False
        self.reconnect_attempt = 0
        self.peer_disconnected = False
        self.disconnect_time = None
        thread = threading.Thread(
            target=self._connect_thread, args=(host, port), daemon=True
        )
        thread.start()

    def _connect_thread(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((host, port))
            self.socket.settimeout(0.5)
            self.connected = True
            self.last_pong_received = time.time()
            self.last_ping_sent = time.time()
            self._receive_loop()
        except Exception as e:
            self.error = str(e)
            self.connected = False

        # Connection lost — try reconnect if not graceful
        if self.running and not self.peer_disconnected:
            self._attempt_reconnect()

    def _receive_loop(self):
        while self.running and self.connected:
            try:
                data = _recv_msg(self.socket)
                if data is None:
                    self.connected = False
                    break

                if isinstance(data, NetworkMessage):
                    if data.msg_type == "_ping":
                        try:
                            _send_msg(self.socket, NetworkMessage("_pong"))
                        except Exception:
                            pass
                        continue
                    elif data.msg_type == "_pong":
                        self.last_pong_received = time.time()
                        self.ping_ms = int((time.time() - self._ping_send_time) * 1000)
                        continue
                    elif data.msg_type == "_disconnect":
                        reason = data.data.get("reason", "unknown")
                        self.connected = False
                        self.peer_disconnected = True
                        self.disconnect_time = time.time()
                        with self._lock:
                            self.message_queue.append(
                                NetworkMessage("_disconnect",
                                               {"reason": reason,
                                                "reconnect_possible": False})
                            )
                        break
                    elif data.msg_type == "_reconnect_ack":
                        self.reconnecting = False
                        self.reconnect_attempt = 0
                        if self.on_reconnect:
                            self.on_reconnect()
                        with self._lock:
                            self.message_queue.append(
                                NetworkMessage("_reconnect_ack")
                            )
                        continue

                self.last_pong_received = time.time()
                with self._lock:
                    self.message_queue.append(data)

            except socket.timeout:
                now = time.time()
                if now - self.last_ping_sent >= self.PING_INTERVAL:
                    try:
                        self._ping_send_time = now
                        _send_msg(self.socket, NetworkMessage("_ping"))
                        self.last_ping_sent = now
                    except Exception:
                        self.connected = False
                        break

                if now - self.last_pong_received > self.TIMEOUT:
                    self.connected = False
                    break
                continue
            except Exception:
                self.connected = False
                break

    def _attempt_reconnect(self):
        """Try to reconnect to the server."""
        if not self.running or self.peer_disconnected:
            return

        self.reconnecting = True
        self.disconnect_time = time.time()

        if self.on_disconnect:
            self.on_disconnect()

        with self._lock:
            self.message_queue.append(
                NetworkMessage("_disconnect",
                               {"reason": "connection_lost",
                                "reconnect_possible": True})
            )

        while (self.running and self.reconnect_attempt < self.MAX_RECONNECT_ATTEMPTS
               and not self.peer_disconnected):
            self.reconnect_attempt += 1

            with self._lock:
                self.message_queue.append(
                    NetworkMessage("_reconnecting",
                                   {"attempt": self.reconnect_attempt,
                                    "max_attempts": self.MAX_RECONNECT_ATTEMPTS})
                )

            time.sleep(self.RECONNECT_DELAY)

            try:
                if self.socket:
                    try:
                        self.socket.close()
                    except Exception:
                        pass

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)
                self.socket.connect((self._host, self._port))
                self.socket.settimeout(0.5)

                # Send reconnect message
                _send_msg(self.socket, NetworkMessage("_reconnect"))

                self.connected = True
                self.last_pong_received = time.time()
                self.last_ping_sent = time.time()
                self.disconnect_time = None
                self.peer_disconnected = False

                self._receive_loop()
                return

            except Exception:
                continue

        # All attempts failed
        self.reconnecting = False
        if not self.peer_disconnected:
            self.peer_disconnected = True
            with self._lock:
                self.message_queue.append(
                    NetworkMessage("_disconnect",
                                   {"reason": "reconnect_failed",
                                    "reconnect_possible": False})
                )

    def send(self, msg):
        if self.socket and self.connected:
            try:
                _send_msg(self.socket, msg)
            except Exception:
                self.connected = False

    def get_messages(self):
        with self._lock:
            msgs = self.message_queue[:]
            self.message_queue.clear()
        return msgs

    def is_peer_disconnected(self):
        return self.peer_disconnected

    def is_reconnecting(self):
        return self.reconnecting

    def disconnect(self):
        """Graceful disconnect."""
        if self.socket and self.connected:
            try:
                _send_msg(self.socket, NetworkMessage("_disconnect",
                          {"reason": "client_left"}))
            except Exception:
                pass
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass


class UDPPeer:
    """UDP peer for real-time games with timeout detection."""

    TIMEOUT = 5.0
    PING_INTERVAL = 1.0

    def __init__(self, local_port=5556):
        self.local_port = local_port
        self.socket = None
        self.remote_addr = None
        self.running = False
        self.message_queue = []
        self._lock = threading.Lock()
        self.error = None

        self.last_received = 0
        self.peer_disconnected = False
        self.ping_ms = 0
        self._ping_send_time = 0
        self._last_ping_sent = 0

    def start(self, remote_host=None, remote_port=None):
        """Start UDP peer."""
        self.running = True
        self.error = None
        self.peer_disconnected = False
        if remote_host and remote_port:
            self.remote_addr = (remote_host, remote_port)
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout(0.5)
            self.socket.bind(("0.0.0.0", self.local_port))
            self.last_received = time.time()
            thread = threading.Thread(target=self._receive_loop, daemon=True)
            thread.start()
            # Ping thread
            ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
            ping_thread.start()
        except Exception as e:
            self.error = str(e)

    def _ping_loop(self):
        while self.running:
            time.sleep(self.PING_INTERVAL)
            if self.remote_addr:
                try:
                    self._ping_send_time = time.time()
                    self._send_raw(NetworkMessage("_ping"))
                except Exception:
                    pass

                # Check timeout
                if time.time() - self.last_received > self.TIMEOUT:
                    if not self.peer_disconnected:
                        self.peer_disconnected = True
                        with self._lock:
                            self.message_queue.append(
                                NetworkMessage("_disconnect",
                                               {"reason": "timeout"})
                            )

    def _receive_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                msg = pickle.loads(data)
                self.last_received = time.time()

                if self.remote_addr is None:
                    self.remote_addr = addr

                # Reset disconnect state on receiving data
                if self.peer_disconnected:
                    self.peer_disconnected = False
                    with self._lock:
                        self.message_queue.append(
                            NetworkMessage("_reconnect_ack")
                        )

                if isinstance(msg, NetworkMessage):
                    if msg.msg_type == "_ping":
                        self._send_raw(NetworkMessage("_pong"))
                        continue
                    elif msg.msg_type == "_pong":
                        self.ping_ms = int((time.time() - self._ping_send_time) * 1000)
                        continue
                    elif msg.msg_type == "_disconnect":
                        self.peer_disconnected = True

                with self._lock:
                    self.message_queue.append(msg)
            except socket.timeout:
                continue
            except Exception:
                continue

    def _send_raw(self, msg):
        if self.socket and self.remote_addr:
            data = pickle.dumps(msg)
            self.socket.sendto(data, self.remote_addr)

    def send(self, msg):
        self._send_raw(msg)

    def get_messages(self):
        with self._lock:
            msgs = self.message_queue[:]
            self.message_queue.clear()
        return msgs

    def is_peer_disconnected(self):
        return self.peer_disconnected

    def stop(self):
        if self.remote_addr:
            try:
                self._send_raw(NetworkMessage("_disconnect",
                               {"reason": "peer_left"}))
            except Exception:
                pass
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass


# === Shared helpers ===

def _send_msg(sock, msg):
    """Send a length-prefixed pickled message over TCP."""
    data = pickle.dumps(msg)
    length = struct.pack("!I", len(data))
    sock.sendall(length + data)


def _recv_msg(sock):
    """Receive a length-prefixed pickled message over TCP."""
    raw_len = _recv_all(sock, 4)
    if raw_len is None:
        return None
    length = struct.unpack("!I", raw_len)[0]
    if length > 10 * 1024 * 1024:  # 10MB safety limit
        return None
    data = _recv_all(sock, length)
    if data is None:
        return None
    return pickle.loads(data)


def _recv_all(sock, n):
    """Receive exactly n bytes."""
    data = b""
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        except socket.timeout:
            continue
        except Exception:
            return None
    return data