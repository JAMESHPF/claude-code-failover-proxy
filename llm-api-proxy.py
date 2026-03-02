#!/usr/bin/env python3
"""
LLM API Failover Proxy
A lightweight, zero-dependency HTTP proxy for LLM API services
with automatic failover, model name mapping, and configuration validation.
"""

__version__ = "2.5.0"

import argparse
import json
import logging
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import socket
import time

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Circuit breaker state: {endpoint_name: {"failures": int, "last_failure": float}}
_circuit_breaker = {}

VALID_AUTH_TYPES = ("anthropic", "openai")

# Default config file search paths
DEFAULT_CONFIG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.expanduser("~/.llm-proxy-config.json"),
]

# Default env file search paths
DEFAULT_ENV_PATHS = [
    os.path.join(os.getcwd(), ".env"),
    os.path.expanduser("~/.llm-proxy.env"),
]

# Default configuration
DEFAULT_CONFIG = {
    "proxy": {
        "host": "127.0.0.1",
        "port": 5000,
        "timeout": 15
    },
    "endpoints": []
}


def find_config_file():
    """Find config file from default paths."""
    for path in DEFAULT_CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def load_env_file(env_file=None):
    """Load environment variables from .env file."""
    if env_file:
        paths = [env_file]
    else:
        paths = DEFAULT_ENV_PATHS

    for path in paths:
        if os.path.exists(path):
            count = 0
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, _, value = line.partition('=')
                            key = key.strip()
                            value = value.strip()
                            if not key:
                                continue
                            # Strip surrounding quotes ("..." or '...')
                            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                                value = value[1:-1]
                            os.environ[key] = value
                            count += 1
                logger.info(f"Loaded {count} env vars from {path}")
                return path
            except Exception as e:
                logger.warning(f"Failed to load env file {path}: {e}")
                return None

    return None


def validate_config(config):
    """Validate configuration completeness and correctness."""
    errors = []
    warnings = []

    # Check required top-level fields
    if "proxy" not in config:
        errors.append("Missing 'proxy' section")
    else:
        proxy = config["proxy"]
        if "host" in proxy and not isinstance(proxy["host"], str):
            errors.append("proxy.host must be a string")
        if "port" in proxy and not isinstance(proxy["port"], int):
            errors.append("proxy.port must be an integer")
        if "timeout" in proxy and not isinstance(proxy["timeout"], (int, float)):
            errors.append("proxy.timeout must be a number")

    if "endpoints" not in config:
        errors.append("Missing 'endpoints' section")
    elif not isinstance(config["endpoints"], list):
        errors.append("'endpoints' must be an array")
    elif len(config["endpoints"]) == 0:
        warnings.append("'endpoints' array is empty, proxy will not work")
    else:
        for i, endpoint in enumerate(config["endpoints"]):
            eid = f"Endpoint #{i+1}"

            if "name" not in endpoint:
                errors.append(f"{eid}: missing 'name'")
            elif not isinstance(endpoint["name"], str):
                errors.append(f"{eid}: 'name' must be a string")
            else:
                eid = f"Endpoint '{endpoint['name']}'"

            if "base_url" not in endpoint:
                errors.append(f"{eid}: missing 'base_url'")
            elif not isinstance(endpoint["base_url"], str):
                errors.append(f"{eid}: 'base_url' must be a string")
            else:
                url = endpoint["base_url"]
                if not url.startswith("http://") and not url.startswith("https://"):
                    errors.append(f"{eid}: 'base_url' must start with http:// or https://")
                if url.endswith("/"):
                    warnings.append(f"{eid}: 'base_url' should not end with /")

            if "api_key" not in endpoint and "api_key_env" not in endpoint:
                errors.append(f"{eid}: must have 'api_key' or 'api_key_env'")

            if "api_key" in endpoint and not isinstance(endpoint["api_key"], str):
                errors.append(f"{eid}: 'api_key' must be a string")

            if "api_key_env" in endpoint and not isinstance(endpoint["api_key_env"], str):
                errors.append(f"{eid}: 'api_key_env' must be a string")

            if "auth_type" in endpoint:
                if endpoint["auth_type"] not in VALID_AUTH_TYPES:
                    errors.append(f"{eid}: 'auth_type' must be one of {VALID_AUTH_TYPES}")

            if "model_mapping" in endpoint:
                if not isinstance(endpoint["model_mapping"], dict):
                    errors.append(f"{eid}: 'model_mapping' must be an object")
                else:
                    for key, value in endpoint["model_mapping"].items():
                        if not isinstance(key, str) or not isinstance(value, str):
                            errors.append(f"{eid}: 'model_mapping' keys and values must be strings")
                            break

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        if warnings:
            logger.warning("Configuration warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        logger.error("\nPlease fix the configuration file and try again")
        sys.exit(1)

    if warnings:
        logger.warning("Configuration warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")

    logger.info("Configuration validation passed")
    return True


def load_config(config_file):
    """Load configuration file."""
    if not os.path.exists(config_file):
        logger.warning(f"Config file not found: {config_file}")
        logger.info("Using default configuration")
        return DEFAULT_CONFIG

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Config loaded: {config_file}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        logger.error(f"  Location: line {e.lineno}, column {e.colno}")
        logger.error(f"\nTip: validate with: python3 -m json.tool {config_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.info("Using default configuration")
        return DEFAULT_CONFIG


def resolve_api_key(endpoint):
    """Resolve API key from environment variable or direct config."""
    if "api_key_env" in endpoint:
        env_var = endpoint["api_key_env"]
        api_key = os.environ.get(env_var)
        if api_key:
            return api_key
        logger.warning(f"Environment variable {env_var} not set")

    if "api_key" in endpoint:
        return endpoint["api_key"]

    logger.error(f"No API key for endpoint: {endpoint.get('name', 'unknown')}")
    return None


def apply_model_mapping(endpoint, body_data):
    """Apply model name mapping if configured."""
    if "model_mapping" not in endpoint:
        return body_data

    model_mapping = endpoint["model_mapping"]
    if "model" in body_data and body_data["model"] in model_mapping:
        original = body_data["model"]
        mapped = model_mapping[original]
        body_data["model"] = mapped
        logger.info(f"  Model mapping: {original} -> {mapped}")

    return body_data


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP proxy request handler."""

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        self._handle_request(method='GET')

    def do_POST(self):
        self._handle_request(method='POST')

    def _handle_request(self, method='POST'):
        try:
            body = None
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)

            config = self.server.config
            endpoints = config.get("endpoints", [])
            proxy_config = config.get("proxy", {})
            timeout = proxy_config.get("timeout", 15)
            cb_threshold = proxy_config.get("circuit_breaker_threshold", 3)
            cb_cooldown = proxy_config.get("circuit_breaker_cooldown", 60)

            for endpoint in endpoints:
                name = endpoint.get("name", "unknown")

                # Circuit breaker check
                cb_state = _circuit_breaker.get(name)
                if cb_state and cb_state["failures"] >= cb_threshold:
                    elapsed = time.time() - cb_state["last_failure"]
                    if elapsed < cb_cooldown:
                        logger.debug(f"Circuit breaker open: {name} (retry in {cb_cooldown - elapsed:.0f}s)")
                        continue
                    logger.info(f"Circuit breaker half-open: retrying {name}")

                api_key = resolve_api_key(endpoint)
                if not api_key:
                    continue

                try:
                    response_iter, status_code, resp_headers = self._forward_request(
                        endpoint, api_key, body, timeout, method
                    )
                    is_streaming = 'text/event-stream' in resp_headers.get('Content-Type', '')
                    self._send_response(response_iter, status_code, resp_headers, is_streaming)
                    _circuit_breaker.pop(name, None)
                    logger.info(f"Success: {name}{' (streaming)' if is_streaming else ''}")
                    return

                except Exception as e:
                    state = _circuit_breaker.setdefault(name, {"failures": 0, "last_failure": 0})
                    state["failures"] += 1
                    state["last_failure"] = time.time()
                    logger.warning(f"Failed: {name} - {e} (failures: {state['failures']}/{cb_threshold})")
                    continue

            error_msg = json.dumps({
                "error": {
                    "message": "All API endpoints unavailable",
                    "type": "service_unavailable"
                }
            }).encode('utf-8')

            self._send_response(error_msg, 503, {'Content-Type': 'application/json'})
            logger.error("All API endpoints unavailable")

        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

    def _forward_request(self, endpoint, api_key, body, timeout, method='POST'):
        if body is not None:
            try:
                body_data = json.loads(body)
                body_data = apply_model_mapping(endpoint, body_data)
                body = json.dumps(body_data).encode('utf-8')
            except json.JSONDecodeError:
                pass

        target_url = f"{endpoint['base_url']}{self.path}"
        auth_type = endpoint.get("auth_type", "anthropic")

        headers = {
            'User-Agent': f'LLM-API-Failover-Proxy/{__version__}'
        }

        if body is not None:
            headers['Content-Type'] = self.headers.get('Content-Type', 'application/json')

        if auth_type == "openai":
            headers['Authorization'] = f'Bearer {api_key}'
        else:
            headers['x-api-key'] = api_key
            headers['anthropic-version'] = self.headers.get('anthropic-version', '2023-06-01')
            anthropic_beta = self.headers.get('anthropic-beta')
            if anthropic_beta:
                headers['anthropic-beta'] = anthropic_beta

        req = Request(target_url, data=body, headers=headers, method=method)
        response = urlopen(req, timeout=timeout)

        def response_iterator():
            try:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                response.close()

        return response_iterator(), response.status, dict(response.headers)

    def _send_response(self, data_or_iter, status_code, headers, is_streaming=False):
        self.send_response(status_code)
        for key, value in headers.items():
            if key.lower() not in ['connection', 'content-length', 'transfer-encoding']:
                self.send_header(key, value)

        if is_streaming:
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self._write_streaming(data_or_iter)
        else:
            data = data_or_iter if isinstance(data_or_iter, bytes) else b''.join(data_or_iter)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)

    def _write_streaming(self, chunk_iterator):
        try:
            for chunk in chunk_iterator:
                if not chunk:
                    continue
                self.wfile.write(f"{len(chunk):x}\r\n".encode())
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            logger.warning(f"Client disconnected during streaming")
        finally:
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass


def create_default_config(config_file):
    """Create default configuration file."""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        logger.info(f"Default config created: {config_file}")
        logger.info("Please edit the config file and set up your API endpoints")
    except Exception as e:
        logger.error(f"Failed to create config: {e}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LLM API Failover Proxy - Lightweight API failover proxy for LLM services"
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file (default: ./config.json or ~/.llm-proxy-config.json)",
        default=None
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        help="Override proxy port",
        default=None
    )
    parser.add_argument(
        "--host",
        help="Override proxy host",
        default=None
    )
    parser.add_argument(
        "-e", "--env",
        help="Path to .env file (default: ./.env or ~/.llm-proxy.env)",
        default=None
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create a default configuration file in current directory"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Handle --init
    if args.init:
        config_file = os.path.join(os.getcwd(), "config.json")
        if os.path.exists(config_file):
            logger.error(f"Config file already exists: {config_file}")
            sys.exit(1)
        create_default_config(config_file)
        env_file = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(env_file):
            with open(env_file, 'w') as f:
                f.write("# Add your API keys here\n# EXAMPLE_API_KEY=sk-your-key-here\n")
            os.chmod(env_file, 0o600)
            logger.info(f"Environment file created: {env_file}")
        logger.info("\nNext steps:")
        logger.info("  1. Edit config.json and add your API endpoints")
        logger.info("  2. Edit .env and add your API keys")
        logger.info("  3. Run: python3 llm-api-proxy.py")
        return

    # Find config file
    if args.config:
        config_file = args.config
    else:
        config_file = find_config_file()
        if not config_file:
            config_file = DEFAULT_CONFIG_PATHS[0]

    # Load env file (before config validation, so API keys are available)
    load_env_file(args.env)

    # Load and validate config
    config = load_config(config_file)
    validate_config(config)

    # Apply CLI overrides
    proxy_config = config.get("proxy", {})
    host = args.host or proxy_config.get("host", "127.0.0.1")
    port = args.port or proxy_config.get("port", 5000)

    try:
        httpd = HTTPServer((host, port), ProxyHandler)
        httpd.config_file = config_file
        httpd.config = config

        cb_threshold = proxy_config.get("circuit_breaker_threshold", 3)
        cb_cooldown = proxy_config.get("circuit_breaker_cooldown", 60)

        logger.info(f"LLM API Failover Proxy v{__version__}")
        logger.info(f"Listening on http://{host}:{port}")
        logger.info(f"Endpoints: {len(config.get('endpoints', []))}")
        logger.info(f"Circuit breaker: {cb_threshold} failures / {cb_cooldown}s cooldown")

        for i, endpoint in enumerate(config.get('endpoints', []), 1):
            api_key = resolve_api_key(endpoint)
            status = "OK" if api_key else "NO KEY"
            auth_type = endpoint.get("auth_type", "anthropic")
            extras = f" [{auth_type}]"
            if "model_mapping" in endpoint:
                extras += f" (model mapping: {len(endpoint['model_mapping'])})"
            logger.info(f"  {i}. [{status}] {endpoint['name']} - {endpoint['base_url']}{extras}")

        logger.info("Ready to accept requests")
        httpd.serve_forever()

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        httpd.shutdown()
        sys.exit(0)

    except socket.error as e:
        if e.errno in (48, 98):  # Address already in use (macOS: 48, Linux: 98)
            logger.error(f"Port {port} is already in use")
        else:
            logger.error(f"Socket error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
