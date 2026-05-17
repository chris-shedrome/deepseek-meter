---
name: set-deepseek-cycle
description: Use when the user wants to set the DeepSeek balance query cycle interval, change "查余额周期", or configure automatic balance polling frequency
---

# Set DeepSeek Cycle

## Overview

`CronCreate` tasks carry session-scoped fields and may be cleared on exit. The `set_cycle` MCP tool writes a session-independent task as the final persistent state. This skill syncs the in-memory scheduler first, then lets `set_cycle` write the authoritative file.

## Workflow

Run these steps **in this exact order**:

1. **Call `CronList`** — find all existing balance-related cron tasks (IDs like `deepseek-meter-cycle` or random IDs like `fbbd547d`)
2. **Call `CronDelete(id=...)`** for EACH matching task — remove stale in-memory and file entries
3. **Call `CronCreate`** — create fresh in-memory task (durable=true)
4. **Call `mcp__deepseek-meter__set_cycle(minutes=N)`** — updates config.json AND overwrites scheduled_tasks.json with session-independent task

Step 4 must come LAST because `set_cycle`'s `manage_cycle_task` writes `deepseek-meter-cycle` (no `createdBySessionId`) to the file, ensuring persistence across session restarts.

### CronCreate Prompt

```
Query DeepSeek balance using mcp__deepseek-meter__query_balance tool. Use lang={lang} to match config.json setting. Output the result.
```

Get `lang` from `get_config` if unsure.

### Cron Expression

| Minutes | Expression |
|---------|-----------|
| N (1-59) | `*/N * * * *` |
| 0 (off) | Skip CronCreate, only CronDelete |

### Disabling (minutes=0)

1. Call `CronList` + `CronDelete` for all balance tasks
2. Call `set_cycle(minutes=0)` — writes empty tasks array
3. Do NOT call CronCreate

## Common Mistakes

- Calling `set_cycle` before CronDelete/CronCreate → in-memory scheduler still runs old interval
- Wrong lang in prompt → balance output in wrong language. Always check `get_config` first.
- Creating a new cron without deleting the old one → duplicate jobs
