# deepseek-meter

This project is in MIT license, **free to use, modify, and distribute** for any purpose — personal, educational, or commercial. No permission is required.

本项目为 MIT 协议，**完全自由使用、修改和分发**，可用于个人、教育或商业目的，无需另行授权。

An MCP server for querying DeepSeek account balance through Claude Code. Supports manual queries, scheduled auto-queries, and 13 output languages.

通过 Claude Code 查询 DeepSeek 账户余额的 MCP 服务器。支持手动查询、定时自动查询、13 种语言输出。

## Quick Glance / 速览

| 项目/Item | 内容/Contents |
| --- | --- |
| 余额/Balance | 99 元/CNY 99 |
| 赠送/Grant | 0 元/CNY 0 |
| 充值/Charge | 99 元/CNY 99 |
| 总额/Total | 99 元/CNY 99 |
| 账户状态/Account Status | 可用/Available |


## Install / 安装

Add to your Claude Code MCP config file (`~/.claude.json` or project `.mcp.json`):

在 Claude Code 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "deepseek-meter": {
      "command": "python3",
      "args": ["/home/user/deepseek-meter/deepseek_mcp.py"]
    }
  }
}
```

Restart Claude Code and run `/mcp` to confirm `deepseek-meter` is connected.

重启 Claude Code 后，输入 `/mcp` 确认 `deepseek-meter` 已连接。

## Set API Key / 设置 API Key

Just say something like:

直接输入提示词（大意一致即可）：

```
Set deepseek-meter API key to sk-xxx
设置deepseek-meter的api-key为sk-xxx
```

Or use the slash command (key is encrypted on disk):

或使用斜杠命令（key 会被加密存储）：

```
/set_api_key sk-your-deepseek-api-key
```

Or use the MCP tool directly:

或使用 MCP 工具：

```
mcp__deepseek-meter__set_api_key(session_key="sk-...")
```

The key is validated against the DeepSeek API before saving — invalid keys are rejected.

设置前会先验证 key 是否有效，无效则拒绝保存。

## Query Balance / 查询余额

Just say something like:

直接输入提示词（大意一致即可）：

```
Query DeepSeek balance
查询deepseek余额
```

Or call directly:

或直接调用工具：

```
mcp__deepseek-meter__query_balance()
```

## Scheduled Query / 定时查询

Set an auto-query interval in minutes. Set to 0 to disable:

设置自动查询间隔（分钟），设为 0 则关闭：

Just say something like:

直接输入提示词（大意一致即可）：

```
Set deepseek-meter cycle to 30 minutes
设置deepseek-meter的循环查询周期为30分钟
```

Or use the MCP tool:

或使用 MCP 工具：

```
mcp__deepseek-meter__set_cycle(minutes=30)
```

Check current interval:

查看当前间隔：

Just say something like:

直接输入提示词（大意一致即可）：

```
What's the deepseek-meter query interval
deepseek-meter的查询间隔是多少
```

Or use the MCP tool:

或使用 MCP 工具：

```
mcp__deepseek-meter__get_cycle()
```

### Use Skill (Recommended / 推荐)

Use the `/set-deepseek-cycle` skill and follow the prompt. The skill syncs both the in-memory scheduler and persistent config, so your cycle survives restarts.

输入 `/set-deepseek-cycle` 调用 skill，按提示输入间隔分钟数。Skill 会同步内存中的定时任务和持久化配置，确保重启后不丢失。

## Multi-Language / 多语言

Just say something like — Claude Code's memory system will remember this preference:

直接输入以下提示词（大意一致即可），Claude Code 会启用 memory 记住这个习惯：

```
When I ask in English, reply in English
查询余额时，我问中文，你答中文
```

Or set language before querying:

或在查询余额前设置语言：

```
mcp__deepseek-meter__set_lang(lang="zh-cn")
mcp__deepseek-meter__query_balance()
```

See available languages:

查看可用语言：

```
mcp__deepseek-meter__get_config()
```

Supported languages / 支持的语言:

| Code | Language / 语言 |
|------|------|
| `zh-cn` | 简体中文 |
| `zh-tw` | 繁体中文 |
| `en` | English |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `ru` | Русский |
| `es` | Español |
| `sv` | Svenska |
| `fr` | Français |
| `de` | Deutsch |
| `pl` | Polski |
| `ar` | العربية |
| `fa` | فارسی |

> Claude Code's memory system remembers your language preference, so you don't need to set it every time.
>
> Claude Code 的 memory 系统会自动记住你的语言偏好，后续查询无需每次设置。

## Full Example / 完整示例

```
# 1. Set API Key / 设置 API Key
Set deepseek-meter API key to sk-xxx
设置deepseek-meter的api-key为sk-xxx
→ API key saved and encrypted. / API key 已加密保存。

# 2. Manual query / 手动查询
Query DeepSeek balance
查询deepseek余额
→ Account status: Available / 账户状态: 可用
→   CNY: Total=24.21, Granted=0.00, Topped up=24.21

# 3. Switch to Chinese and query again / 切到中文再查
When I ask in Chinese, reply in Chinese
我问中文时用中文回答
→ 账户状态: 可用
→   CNY: 总额=24.21, 赠送=0.00, 充值=24.21

# 4. Enable 30-minute auto query / 开启每 30 分钟自动查询
Set deepseek-meter cycle to 30 minutes
设置deepseek-meter的循环查询周期为30分钟
→ Cycle query interval set to: 30 minute(s) / 循环查询间隔已设置为：30 分钟
```

## All Tools / 工具列表

| Tool / 工具 | Description / 说明 |
|-------------|-------------------|
| `query_balance` | Query balance / 查询余额 |
| `set_api_key` | Set & encrypt API key / 设置并加密 API Key |
| `set_cycle` | Set cycle interval / 设置定时查询间隔 |
| `get_cycle` | Get cycle interval / 查看定时查询间隔 |
| `set_lang` | Set output language / 设置输出语言 |
| `get_config` | Get current config / 查看当前配置 |
