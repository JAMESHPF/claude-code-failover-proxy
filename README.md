# LLM API Failover Proxy

A lightweight, zero-dependency HTTP proxy for LLM API services with automatic failover, model name mapping, and configuration validation.

[中文文档](README_CN.md)

## Features

- **Automatic Failover**: Seamlessly switches between multiple API endpoints when one fails
- **Model Name Mapping**: Transparently maps model names for APIs with different naming conventions
- **Configuration Validation**: Validates configuration on startup to catch errors early
- **Zero Dependencies**: Uses only Python standard library
- **Environment Variable Support**: Securely manages API keys via environment variables
- **Systemd Integration**: Runs as a system service with auto-restart
- **Detailed Logging**: Clear logs for debugging and monitoring
- **Streaming Support**: Supports SSE streaming responses with chunked transfer encoding for real-time LLM output
- **Circuit Breaker**: Automatically skips failing endpoints after consecutive failures, with configurable threshold and cooldown
- **Multi-Protocol Auth**: Supports both Anthropic (`x-api-key`) and OpenAI (`Authorization: Bearer`) authentication styles
- **GET & POST Support**: Proxies both GET (e.g., `/v1/models`) and POST requests

## Use Cases

- Using multiple third-party LLM API providers (e.g., Claude API resellers)
- Need automatic failover when one provider experiences outages
- Different providers use different model naming conventions
- Running Claude Code or other LLM clients on a VPS
- Want transparent failover without manual configuration changes

## Requirements

- Python 3.7+
- Linux system with systemd (for service mode)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/JAMESHPF/llm-api-failover-proxy.git
   cd llm-api-failover-proxy
   ```

2. **Create configuration file**
   ```bash
   cp config.example.json ~/.llm-proxy-config.json
   # Edit the file and add your API endpoints
   vim ~/.llm-proxy-config.json
   ```

3. **Create environment file**
   ```bash
   cp .env.example ~/.llm-proxy.env
   # Add your API keys
   vim ~/.llm-proxy.env
   chmod 600 ~/.llm-proxy.env
   ```

4. **Test the proxy**
   ```bash
   python3 llm-api-proxy.py
   ```
   The proxy automatically loads `.env` from the current directory or `~/.llm-proxy.env`.

5. **Install as systemd service** (optional)
   ```bash
   sudo cp llm-api-proxy.service /etc/systemd/system/
   # Edit the service file to match your paths
   sudo vim /etc/systemd/system/llm-api-proxy.service
   sudo systemctl daemon-reload
   sudo systemctl enable llm-api-proxy
   sudo systemctl start llm-api-proxy
   ```

## CLI Options

```
usage: llm-api-proxy.py [-h] [-c CONFIG] [-p PORT] [--host HOST] [-e ENV] [-v] [--init]

options:
  -c, --config CONFIG   Path to configuration file
  -p, --port PORT       Override proxy port
  --host HOST           Override proxy host
  -e, --env ENV         Path to .env file
  -v, --version         Show version
  --init                Create default config in current directory
```

## Configuration

### Config File (`~/.llm-proxy-config.json`)

```json
{
  "proxy": {
    "host": "127.0.0.1",
    "port": 5000,
    "timeout": 15,
    "circuit_breaker_threshold": 3,
    "circuit_breaker_cooldown": 60
  },
  "endpoints": [
    {
      "name": "Primary API",
      "base_url": "https://api.example.com",
      "api_key_env": "PRIMARY_API_KEY"
    },
    {
      "name": "Backup API",
      "base_url": "https://backup-api.example.com",
      "api_key_env": "BACKUP_API_KEY",
      "model_mapping": {
        "claude-opus-4-6": "claude-opus-4-6-thinking"
      }
    },
    {
      "name": "OpenAI Compatible",
      "base_url": "https://api.openai.com",
      "api_key_env": "OPENAI_API_KEY",
      "auth_type": "openai"
    }
  ]
}
```

### Environment File (`~/.llm-proxy.env`)

```bash
PRIMARY_API_KEY=sk-your-primary-key
BACKUP_API_KEY=sk-your-backup-key
OPENAI_API_KEY=sk-your-openai-key
```

Quoted values are supported: `KEY="value"` and `KEY='value'` are automatically unquoted.

## Model Name Mapping

Some API providers use different model naming conventions. The proxy can automatically map model names:

```json
{
  "name": "Custom API",
  "base_url": "https://custom-api.com",
  "api_key_env": "CUSTOM_API_KEY",
  "model_mapping": {
    "claude-opus-4-6": "claude-opus-4-6-thinking",
    "claude-sonnet-4-6": "claude-sonnet-4-6-thinking"
  }
}
```

When your client requests `claude-opus-4-6`, the proxy automatically sends `claude-opus-4-6-thinking` to this endpoint.

### Authentication Types

The proxy supports different authentication styles via the `auth_type` endpoint field:

| `auth_type` | Header Sent | Default |
|-------------|-------------|---------|
| `"anthropic"` | `x-api-key` + `anthropic-version` | Yes |
| `"openai"` | `Authorization: Bearer <key>` | No |

```json
{
  "name": "OpenAI Compatible",
  "base_url": "https://api.openai.com",
  "api_key_env": "OPENAI_API_KEY",
  "auth_type": "openai"
}
```

### Circuit Breaker

The proxy includes a circuit breaker to avoid repeatedly hitting failing endpoints:

- After `circuit_breaker_threshold` consecutive failures (default: 3), the endpoint is temporarily skipped
- After `circuit_breaker_cooldown` seconds (default: 60), the endpoint is retried
- On success, the failure count is reset

Configure in the `proxy` section:

```json
{
  "proxy": {
    "circuit_breaker_threshold": 3,
    "circuit_breaker_cooldown": 60
  }
}
```

## Using with Claude Code

Configure Claude Code to use the proxy:

```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:5000",
    "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED"
  }
}
```

## Verification

Test the proxy directly:

```bash
curl -X POST http://127.0.0.1:5000/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"claude-opus-4-6","max_tokens":20,"messages":[{"role":"user","content":"test"}]}'
```

```bash
# Test GET (e.g., list models)
curl http://127.0.0.1:5000/v1/models
```

Check logs:

```bash
# If running as service
journalctl -u llm-api-proxy -f

# If running directly
# Logs are printed to stdout
```

## Troubleshooting

**Port already in use**
- Change the `port` in `config.json`

**All endpoints fail**
- Check API keys in `.env` file
- Verify endpoint URLs are correct
- Check network connectivity

**Service won't start**
- Check logs: `journalctl -u llm-api-proxy -n 50`
- Validate JSON: `python3 -m json.tool < ~/.llm-proxy-config.json`

## Security Notes

- API keys are stored in environment file with 600 permissions
- Config file is separate from code (easier to version control without secrets)
- Proxy binds to 127.0.0.1 only (not accessible from network)
- Never commit `.llm-proxy.env` or `.llm-proxy-config.json` to version control

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
