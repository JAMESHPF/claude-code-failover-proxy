# LLM API Failover Proxy

[English](#english) | [中文](#中文)

---

## English

A lightweight, zero-dependency HTTP proxy for LLM API services with automatic failover, model name mapping, and configuration validation.

### Features

- **Automatic Failover**: Seamlessly switches between multiple API endpoints when one fails
- **Model Name Mapping**: Transparently maps model names for APIs with different naming conventions
- **Configuration Validation**: Validates configuration on startup to catch errors early
- **Zero Dependencies**: Uses only Python standard library
- **Environment Variable Support**: Securely manages API keys via environment variables
- **Systemd Integration**: Runs as a system service with auto-restart
- **Detailed Logging**: Clear logs for debugging and monitoring

### Use Cases

- Using multiple third-party LLM API providers (e.g., Claude API resellers)
- Need automatic failover when one provider experiences outages
- Different providers use different model naming conventions
- Running Claude Code or other LLM clients on a VPS
- Want transparent failover without manual configuration changes

### Requirements

- Python 3.7+
- Linux system with systemd (for service mode)

### Quick Start

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

### CLI Options

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

### Configuration

#### Config File (`~/.llm-proxy-config.json`)

```json
{
  "proxy": {
    "host": "127.0.0.1",
    "port": 5000,
    "timeout": 15
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
    }
  ]
}
```

#### Environment File (`~/.llm-proxy.env`)

```bash
PRIMARY_API_KEY=sk-your-primary-key
BACKUP_API_KEY=sk-your-backup-key
```

### Model Name Mapping

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

### Using with Claude Code

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

### Verification

Test the proxy directly:

```bash
curl -X POST http://127.0.0.1:5000/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"claude-opus-4-6","max_tokens":20,"messages":[{"role":"user","content":"test"}]}'
```

Check logs:

```bash
# If running as service
journalctl -u llm-api-proxy -f

# If running directly
# Logs are printed to stdout
```

### Troubleshooting

**Port already in use**
- Change the `port` in `config.json`

**All endpoints fail**
- Check API keys in `.env` file
- Verify endpoint URLs are correct
- Check network connectivity

**Service won't start**
- Check logs: `journalctl -u llm-api-proxy -n 50`
- Validate JSON: `python3 -m json.tool < ~/.llm-proxy-config.json`

### Security Notes

- API keys are stored in environment file with 600 permissions
- Config file is separate from code (easier to version control without secrets)
- Proxy binds to 127.0.0.1 only (not accessible from network)
- Never commit `.llm-proxy.env` or `.llm-proxy-config.json` to version control

### License

MIT License - see [LICENSE](LICENSE) file for details

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 中文

一个轻量级、零依赖的 LLM API HTTP 代理，支持自动故障转移、模型名称映射和配置验证。

### 功能特性

- **自动故障转移**：当一个 API 端点失败时，无缝切换到其他端点
- **模型名称映射**：透明地为使用不同命名规则的 API 映射模型名称
- **配置验证**：启动时验证配置，及早发现错误
- **零依赖**：仅使用 Python 标准库
- **环境变量支持**：通过环境变量安全管理 API 密钥
- **Systemd 集成**：作为系统服务运行，支持自动重启
- **详细日志**：清晰的日志便于调试和监控

### 使用场景

- 使用多个第三方 LLM API 提供商（如 Claude API 中转服务）
- 需要在某个提供商出现故障时自动切换
- 不同提供商使用不同的模型命名规则
- 在 VPS 上运行 Claude Code 或其他 LLM 客户端
- 希望透明的故障转移，无需手动更改配置

### 系统要求

- Python 3.7+
- Linux 系统（服务模式需要 systemd）

### 快速开始

1. **克隆仓库**
   ```bash
   git clone https://github.com/JAMESHPF/llm-api-failover-proxy.git
   cd llm-api-failover-proxy
   ```

2. **创建配置文件**
   ```bash
   cp config.example.json ~/.llm-proxy-config.json
   # 编辑文件并添加你的 API 端点
   vim ~/.llm-proxy-config.json
   ```

3. **创建环境变量文件**
   ```bash
   cp .env.example ~/.llm-proxy.env
   # 添加你的 API 密钥
   vim ~/.llm-proxy.env
   chmod 600 ~/.llm-proxy.env
   ```

4. **测试代理**
   ```bash
   python3 llm-api-proxy.py
   ```
   代理会自动从当前目录的 `.env` 或 `~/.llm-proxy.env` 加载环境变量。

5. **安装为 systemd 服务**（可选）
   ```bash
   sudo cp llm-api-proxy.service /etc/systemd/system/
   # 编辑服务文件以匹配你的路径
   sudo vim /etc/systemd/system/llm-api-proxy.service
   sudo systemctl daemon-reload
   sudo systemctl enable llm-api-proxy
   sudo systemctl start llm-api-proxy
   ```

### 命令行选项

```
用法: llm-api-proxy.py [-h] [-c CONFIG] [-p PORT] [--host HOST] [-e ENV] [-v] [--init]

选项:
  -c, --config CONFIG   配置文件路径
  -p, --port PORT       覆盖代理端口
  --host HOST           覆盖代理主机
  -e, --env ENV         .env 文件路径
  -v, --version         显示版本
  --init                在当前目录创建默认配置
```

### 配置说明

#### 配置文件 (`~/.llm-proxy-config.json`)

```json
{
  "proxy": {
    "host": "127.0.0.1",
    "port": 5000,
    "timeout": 15
  },
  "endpoints": [
    {
      "name": "主要 API",
      "base_url": "https://api.example.com",
      "api_key_env": "PRIMARY_API_KEY"
    },
    {
      "name": "备用 API",
      "base_url": "https://backup-api.example.com",
      "api_key_env": "BACKUP_API_KEY",
      "model_mapping": {
        "claude-opus-4-6": "claude-opus-4-6-thinking"
      }
    }
  ]
}
```

#### 环境变量文件 (`~/.llm-proxy.env`)

```bash
PRIMARY_API_KEY=sk-your-primary-key
BACKUP_API_KEY=sk-your-backup-key
```

### 模型名称映射

某些 API 提供商使用不同的模型命名规则。代理可以自动映射模型名称：

```json
{
  "name": "自定义 API",
  "base_url": "https://custom-api.com",
  "api_key_env": "CUSTOM_API_KEY",
  "model_mapping": {
    "claude-opus-4-6": "claude-opus-4-6-thinking",
    "claude-sonnet-4-6": "claude-sonnet-4-6-thinking"
  }
}
```

当客户端请求 `claude-opus-4-6` 时，代理会自动向该端点发送 `claude-opus-4-6-thinking`。

### 与 Claude Code 配合使用

配置 Claude Code 使用代理：

```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:5000",
    "ANTHROPIC_AUTH_TOKEN": "PROXY_MANAGED"
  }
}
```

### 验证

直接测试代理：

```bash
curl -X POST http://127.0.0.1:5000/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"claude-opus-4-6","max_tokens":20,"messages":[{"role":"user","content":"test"}]}'
```

查看日志：

```bash
# 如果作为服务运行
journalctl -u llm-api-proxy -f

# 如果直接运行
# 日志会打印到标准输出
```

### 故障排查

**端口已被占用**
- 修改 `config.json` 中的 `port`

**所有端点都失败**
- 检查 `.env` 文件中的 API 密钥
- 验证端点 URL 是否正确
- 检查网络连接

**服务无法启动**
- 查看日志：`journalctl -u llm-api-proxy -n 50`
- 验证 JSON 格式：`python3 -m json.tool < ~/.llm-proxy-config.json`

### 安全说明

- API 密钥存储在权限为 600 的环境变量文件中
- 配置文件与代码分离（便于版本控制而不包含密钥）
- 代理仅绑定到 127.0.0.1（不可从网络访问）
- 永远不要将 `.llm-proxy.env` 或 `.llm-proxy-config.json` 提交到版本控制

### 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

### 贡献

欢迎贡献！请随时提交 Pull Request。
