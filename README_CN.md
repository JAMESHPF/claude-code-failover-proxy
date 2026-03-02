# LLM API 故障转移代理

一个轻量级、零依赖的 LLM API HTTP 代理，支持自动故障转移、模型名称映射和配置验证。

[English Documentation](README.md)

## 功能特性

- **自动故障转移**：当一个 API 端点失败时，无缝切换到其他端点
- **模型名称映射**：透明地为使用不同命名规则的 API 映射模型名称
- **配置验证**：启动时验证配置，及早发现错误
- **零依赖**：仅使用 Python 标准库
- **环境变量支持**：通过环境变量安全管理 API 密钥
- **Systemd 集成**：作为系统服务运行，支持自动重启
- **详细日志**：清晰的日志便于调试和监控
- **流式响应**：支持 SSE 流式传输，使用 chunked 编码实时输出 LLM 响应
- **断路器保护**：连续失败后自动跳过故障端点，支持配置阈值和冷却时间
- **多协议认证**：同时支持 Anthropic（`x-api-key`）和 OpenAI（`Authorization: Bearer`）认证方式
- **GET/POST 支持**：代理 GET（如 `/v1/models`）和 POST 请求

## 使用场景

- 使用多个第三方 LLM API 提供商（如 Claude API 中转服务）
- 需要在某个提供商出现故障时自动切换
- 不同提供商使用不同的模型命名规则
- 在 VPS 上运行 Claude Code 或其他 LLM 客户端
- 希望透明的故障转移，无需手动更改配置

## 系统要求

- Python 3.7+
- Linux 系统（服务模式需要 systemd）

## 快速开始

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

## 命令行选项

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

## 配置说明

### 配置文件 (`~/.llm-proxy-config.json`)

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
    },
    {
      "name": "OpenAI 兼容 API",
      "base_url": "https://api.openai.com",
      "api_key_env": "OPENAI_API_KEY",
      "auth_type": "openai"
    }
  ]
}
```

### 环境变量文件 (`~/.llm-proxy.env`)

```bash
PRIMARY_API_KEY=sk-your-primary-key
BACKUP_API_KEY=sk-your-backup-key
OPENAI_API_KEY=sk-your-openai-key
```

支持带引号的值：`KEY="value"` 和 `KEY='value'` 会自动去除引号。

## 模型名称映射

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

### 认证方式

代理通过 endpoint 的 `auth_type` 字段支持不同认证方式：

| `auth_type` | 发送的请求头 | 默认 |
|-------------|-------------|------|
| `"anthropic"` | `x-api-key` + `anthropic-version` | 是 |
| `"openai"` | `Authorization: Bearer <key>` | 否 |

```json
{
  "name": "OpenAI 兼容 API",
  "base_url": "https://api.openai.com",
  "api_key_env": "OPENAI_API_KEY",
  "auth_type": "openai"
}
```

### 断路器

代理内置断路器机制，避免反复请求故障端点：

- 连续失败 `circuit_breaker_threshold` 次后（默认 3），自动跳过该端点
- 冷却 `circuit_breaker_cooldown` 秒后（默认 60），重新尝试
- 请求成功后，失败计数归零

在 `proxy` 配置中设置：

```json
{
  "proxy": {
    "circuit_breaker_threshold": 3,
    "circuit_breaker_cooldown": 60
  }
}
```

## 与 Claude Code 配合使用

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

## 验证

直接测试代理：

```bash
curl -X POST http://127.0.0.1:5000/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{"model":"claude-opus-4-6","max_tokens":20,"messages":[{"role":"user","content":"test"}]}'
```

```bash
# 测试 GET 请求（如列出模型）
curl http://127.0.0.1:5000/v1/models
```

查看日志：

```bash
# 如果作为服务运行
journalctl -u llm-api-proxy -f

# 如果直接运行
# 日志会打印到标准输出
```

## 故障排查

**端口已被占用**
- 修改 `config.json` 中的 `port`

**所有端点都失败**
- 检查 `.env` 文件中的 API 密钥
- 验证端点 URL 是否正确
- 检查网络连接

**服务无法启动**
- 查看日志：`journalctl -u llm-api-proxy -n 50`
- 验证 JSON 格式：`python3 -m json.tool < ~/.llm-proxy-config.json`

## 安全说明

- API 密钥存储在权限为 600 的环境变量文件中
- 配置文件与代码分离（便于版本控制而不包含密钥）
- 代理仅绑定到 127.0.0.1（不可从网络访问）
- 永远不要将 `.llm-proxy.env` 或 `.llm-proxy-config.json` 提交到版本控制

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎贡献！请随时提交 Pull Request。
