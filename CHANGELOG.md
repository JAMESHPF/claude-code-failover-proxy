# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-03-03

### Added
- **Concurrent request handling** with `ThreadingHTTPServer` (no more blocking on streaming)
- **`/_proxy/health`** endpoint returning status, version, uptime
- **`/_proxy/status`** endpoint with per-endpoint stats, circuit breaker states, request counts
- **Request ID** (`[a1b2c3d4]`) in all log lines for request tracing
- **Request latency** and endpoint name in success/failure logs
- **Detailed failure summary** when all endpoints are exhausted, listing each attempt
- **`--log-level`** CLI parameter and `PROXY_LOG_LEVEL` env var
- **`--validate`** mode to check config without starting the server
- **Per-endpoint `timeout`** configuration (overrides global timeout)
- **Environment variable overrides**: `PROXY_TIMEOUT`, `PROXY_CB_THRESHOLD`, `PROXY_CB_COOLDOWN`, `PROXY_MAX_BODY_SIZE`
- **SIGHUP hot reload** for config changes without restart
- **SIGTERM graceful shutdown** waits for in-flight requests
- **Request statistics** tracking per endpoint (success, fail_5xx, fail_4xx, fail_conn)
- Thread-safe shared state with `threading.Lock`
- `log_error` override to route all logs through logging framework

### Changed
- Server class changed from `HTTPServer` to `ThreadingHTTPServer`
- Circuit breaker now resets `failures=0` on success instead of removing the entry (preserves stats)
- Startup log now shows per-endpoint timeout, threading status, and management URLs

## [2.6.0] - 2026-03-02

### Fixed
- Circuit breaker no longer trips on HTTP 4xx errors (endpoint is healthy, issue is client-side or auth)
- Upstream error responses (status code + body) are now forwarded to client instead of generic 503
- `--port 0` and `--host ""` CLI overrides no longer silently fall back to defaults

### Added
- Smart error classification: 5xx + connection errors trip circuit breaker; 401/403/429 retry next endpoint without tripping; 400/404/422 forward directly to client
- `max_body_size` proxy config option (default 50MB) to reject oversized requests with HTTP 413

### Changed
- Systemd service file default user changed from `root` to `llmproxy` for security
- `.env.example` instructions updated to reflect both `.env` and `~/.llm-proxy.env` load paths

### Removed
- Accidentally committed `__pycache__/` directory

## [2.5.0] - 2026-03-02

### Added
- GET method support for proxying requests like `/v1/models`
- `.env` file quote handling: `KEY="value"` and `KEY='value'` are automatically unquoted

## [2.4.0] - 2026-03-02

### Added
- `auth_type` endpoint configuration supporting `"anthropic"` (default) and `"openai"` authentication
- OpenAI-compatible authentication with `Authorization: Bearer` header
- `anthropic-beta` header forwarding for Anthropic endpoints
- Circuit breaker pattern to skip failing endpoints after consecutive failures
- `circuit_breaker_threshold` proxy configuration (default: 3)
- `circuit_breaker_cooldown` proxy configuration (default: 60 seconds)
- Failure count logging per endpoint (e.g., `failures: 1/3`)

## [2.3.0] - 2026-03-02

### Added
- Streaming response support with chunked transfer encoding (SSE/text-event-stream)
- Real-time LLM output forwarding via `_write_streaming()` method

### Changed
- Configuration loaded once at startup instead of per-request (performance optimization)
- `_forward_request()` returns response iterator instead of buffered bytes
- `_send_response()` supports both streaming and non-streaming modes

## [2.2.0] - 2026-03-02

### Added
- Automatic `.env` file loading from current directory or `~/.llm-proxy.env`
- `-e/--env` CLI option to specify custom .env file path
- CLI options documentation in README

### Changed
- Improved systemd service file with comments for easier customization
- Version bumped to 2.2.0

## [2.1.0] - 2026-03-02

### Added
- Command-line argument parsing with argparse
- `-c/--config` option to specify config file path
- `-p/--port` option to override proxy port
- `--host` option to override proxy host
- `-v/--version` option to show version
- `--init` flag to create default config in current directory
- Flexible config file path resolution (searches `./config.json` and `~/.llm-proxy-config.json`)
- User-Agent header with version info

### Changed
- Internationalized all log messages to English
- Removed hardcoded personal API endpoints from default config
- Empty default endpoints array instead of personal endpoints
- Fixed port-in-use errno for both macOS (48) and Linux (98)

## [2.0.0] - 2026-03-01

### Added
- Model name mapping feature for per-endpoint model translation
- Configuration validation on startup with detailed error/warning messages
- `model_mapping` field in endpoint configuration
- `apply_model_mapping()` function for transparent model name translation

### Changed
- Enhanced error messages with specific validation feedback
- Improved logging with structured validation output

## [1.0.0] - 2026-02-28

### Added
- Initial release
- Automatic failover between multiple API endpoints
- Zero-dependency implementation using Python standard library
- Environment variable support for API keys
- Systemd service integration
- Detailed logging for debugging and monitoring
- Support for Claude API and compatible services
