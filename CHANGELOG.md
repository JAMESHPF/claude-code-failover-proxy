# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
