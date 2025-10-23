"""WiFi manager for BadOS targeting Pico W (CircuitPython wifi API)

Provides a small WiFiManager class to connect/disconnect and create a
SocketPool for networking. Automatically loads credentials from config/wifi.json.
"""

try:
    import wifi
    import socketpool
except Exception:
    wifi = None
    socketpool = None

import json


class WiFiManager:
    def __init__(self, config_path="/config/wifi.json"):
        """Initialize WiFi manager.

        Args:
            config_path: Path to wifi.json configuration file
        """
        self._radio = wifi.radio if wifi else None
        self._pool = None
        self._config_path = config_path
        self._credentials = self._load_credentials()

    def _load_credentials(self):
        """Load WiFi credentials from config file.

        Returns dict with 'ssid' and 'password' or None if failed.
        """
        try:
            with open(self._config_path, 'r') as f:
                creds = json.load(f)
                if 'ssid' in creds and 'password' in creds:
                    return creds
                else:
                    print(f"WiFi config missing ssid/password in {self._config_path}")
                    return None
        except Exception as e:
            print(f"Failed to load WiFi config from {self._config_path}: {e}")
            return None

    def connect(self, ssid=None, password=None, timeout=10):
        """Connect to WiFi network.

        Args:
            ssid: Network SSID (uses config file if not provided)
            password: Network password (uses config file if not provided)
            timeout: Connection timeout in seconds

        Returns True on success, False on failure.
        """
        if not self._radio:
            raise RuntimeError("WiFi not available on this build")

        # Use provided credentials or fall back to config file
        if ssid is None or password is None:
            if self._credentials is None:
                print("No WiFi credentials available")
                return False
            ssid = ssid or self._credentials['ssid']
            password = password or self._credentials['password']

        try:
            print(f"Connecting to {ssid}...")
            self._radio.connect(ssid=ssid, password=password, timeout=timeout)
            self._pool = socketpool.SocketPool(self._radio)
            print(f"Connected! IP: {self.get_ip()}")
            return True
        except Exception as e:
            print(f"WiFi connection failed: {e}")
            # Attempt disable/enable radio to clear state
            try:
                self._radio.enabled = False
                self._radio.enabled = True
            except Exception:
                pass
            return False

    def is_connected(self):
        """Check if WiFi is connected.

        Returns True if connected, False otherwise.
        """
        if not self._radio:
            return False
        try:
            return bool(self._radio.connected)
        except Exception:
            return False

    def get_ip(self):
        """Get current IP address.

        Returns IP address string or None if not connected.
        """
        if not self._radio:
            return None
        try:
            return str(self._radio.ipv4_address) if self._radio.ipv4_address else None
        except Exception:
            return None

    def get_rssi(self):
        """Get WiFi signal strength (RSSI).

        Returns RSSI in dBm or None if not available.
        """
        if not self._radio:
            return None
        try:
            if hasattr(self._radio, 'ap_info') and self._radio.ap_info:
                return self._radio.ap_info.rssi
        except (NotImplementedError, AttributeError):
            # Some boards don't support RSSI reading
            pass
        return None

    def socket_pool(self):
        """Get socket pool for network operations.

        Returns SocketPool instance or None if not connected.
        """
        # If we don't have a pool but WiFi is connected, create one
        if self._pool is None and self.is_connected():
            try:
                self._pool = socketpool.SocketPool(self._radio)
            except Exception:
                return None
        return self._pool

    def disconnect(self):
        """Disconnect from WiFi network.

        Returns True on success, False on failure.
        """
        if not self._radio:
            return False
        try:
            self._radio.disconnect()
            self._pool = None
            print("WiFi disconnected")
            return True
        except Exception:
            return False

    def scan_networks(self, show_hidden=False):
        """Scan for available WiFi networks.

        Args:
            show_hidden: Include hidden networks

        Returns list of network info dicts or empty list on failure.
        """
        if not self._radio:
            return []
        try:
            networks = []
            for network in self._radio.start_scanning_networks():
                if not show_hidden and not network.ssid:
                    continue
                networks.append({
                    'ssid': network.ssid,
                    'rssi': network.rssi,
                    'channel': network.channel
                })
            self._radio.stop_scanning_networks()
            return networks
        except Exception as e:
            print(f"Network scan failed: {e}")
            return []
