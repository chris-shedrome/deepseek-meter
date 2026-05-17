#!/usr/bin/env python3
"""MCP server for DeepSeek account balance query."""
import json
import sys
import os
import time
import hashlib
import base64
import uuid
import socket
import urllib.request
import urllib.error
from cryptography.fernet import Fernet, InvalidToken

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(SCRIPT_DIR, "key.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
BALANCE_URL = "https://api.deepseek.com/user/balance"


def derive_key():
    mac = str(uuid.getnode())
    hostname = socket.gethostname()
    digest = hashlib.sha256(f"{mac}:{hostname}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


def save_encrypted(api_key):
    fernet = Fernet(derive_key())
    data = json.dumps({"api_key": api_key}).encode()
    with open(KEY_FILE, "wb") as f:
        f.write(fernet.encrypt(data))

SCHEDULED_TASKS_FILE = os.path.expanduser("~/.claude/scheduled_tasks.json")
CYCLE_TASK_ID = "deepseek-meter-cycle"

LANGUAGES = {}
MESSAGES = {}


def load_translations():
    global LANGUAGES, MESSAGES
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        LANGUAGES = cfg.get("languages", {})
        MESSAGES = cfg.get("messages", {})
    except Exception:
        pass


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if k not in ("messages", "languages")}, None
    except FileNotFoundError:
        return {"lang": "en"}, None
    except json.JSONDecodeError as e:
        return {"lang": "en"}, str(e)


def save_config(cfg):
    full = {
        **{k: v for k, v in cfg.items() if k not in ("messages", "languages")},
        "messages": MESSAGES,
        "languages": LANGUAGES,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(full, f, indent=2, ensure_ascii=False)


def t(key, lang, *args):
    text = MESSAGES.get(key, {}).get(lang, MESSAGES.get(key, {}).get("en", key))
    if args:
        return text.format(*args)
    return text


def load_api_key(lang):
    if not os.path.exists(KEY_FILE):
        return None, t("key_not_found", lang, KEY_FILE)
    try:
        with open(KEY_FILE, "rb") as f:
            raw = f.read()
    except Exception:
        return None, t("key_read_error", lang)

    if not raw.strip():
        return None, t("key_not_found", lang, KEY_FILE)

    # Try Fernet decrypt
    try:
        decrypted = Fernet(derive_key()).decrypt(raw).decode()
        data = json.loads(decrypted)
        key = data.get("api_key", "").strip()
        if not key or key == "YOUR_DEEPSEEK_API_KEY_HERE":
            return None, t("set_api_key", lang)
        return key, None
    except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError):
        pass

    # Fallback: plaintext JSON (auto-migrate)
    try:
        data = json.loads(raw.decode())
        key = data.get("api_key", "").strip()
        if not key or key == "YOUR_DEEPSEEK_API_KEY_HERE":
            return None, t("set_api_key", lang)
        save_encrypted(key)
        return key, None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, t("key_invalid_json", lang)


def query_balance(api_key):
    req = urllib.request.Request(
        BALANCE_URL,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return e.code, None, f"HTTP {e.code}: {body}"
    except urllib.error.URLError as e:
        return 0, None, str(e.reason)
    except Exception as e:
        return 0, None, str(e)


def load_scheduled_tasks():
    try:
        with open(SCHEDULED_TASKS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tasks": []}


def save_scheduled_tasks(data):
    os.makedirs(os.path.dirname(SCHEDULED_TASKS_FILE), exist_ok=True)
    with open(SCHEDULED_TASKS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def manage_cycle_task(minutes, lang):
    """Create, update, or delete the cycle cron job in Claude Code's scheduled_tasks.json."""
    data = load_scheduled_tasks()
    tasks = data.get("tasks", [])

    # Remove existing cycle task (by id) and any CronCreate tasks with same prompt
    tasks = [
        t for t in tasks
        if t.get("id") != CYCLE_TASK_ID
        and "mcp__deepseek-meter__query_balance" not in t.get("prompt", "")
    ]

    if minutes > 0:
        cron_expr = f"*/{minutes} * * * *" if minutes <= 59 else f"0 */{minutes // 60} * * *"
        prompt = (
            f"Query DeepSeek balance using mcp__deepseek-meter__query_balance tool. "
            f"Use lang={lang} to match config.json setting. Output the result."
        )
        now_ms = int(time.time() * 1000)
        task = {
            "id": CYCLE_TASK_ID,
            "cron": cron_expr,
            "prompt": prompt,
            "createdAt": now_ms,
            "recurring": True,
        }
        tasks.append(task)

    data["tasks"] = tasks
    save_scheduled_tasks(data)


def format_balance(data, lang):
    available = data.get("is_available", False)
    status = t("available_yes", lang) if available else t("available_no", lang)
    lines = [f"{t('status', lang)}: {status}"]
    for info in data.get("balance_infos", []):
        currency = info.get("currency", "?")
        total = info.get("total_balance", "0.00")
        granted = info.get("granted_balance", "0.00")
        topped = info.get("topped_up_balance", "0.00")
        lines.append(
            f"  {currency}: {t('total', lang)}={total}, "
            f"{t('granted', lang)}={granted}, {t('topped_up', lang)}={topped}"
        )
    return "\n".join(lines) if len(lines) > 1 else t("no_balance", lang)


# ---- MCP JSON-RPC over stdio ----

def send(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    if error:
        msg["error"] = {"code": error[0], "message": error[1]}
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    load_translations()

    buffer = ""
    for line in sys.stdin:
        buffer += line
        try:
            msg = json.loads(buffer)
            buffer = ""
        except json.JSONDecodeError:
            continue

        mid = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            send(mid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "deepseek-meter", "version": "1.5.0"},
            })
        elif method == "tools/list":
            send(mid, {
                "tools": [
                    {
                        "name": "query_balance",
                        "description": "Query DeepSeek account balance. Uses config.json lang by default.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "lang": {
                                    "type": "string",
                                    "description": "Output language override",
                                    "enum": list(LANGUAGES.keys()),
                                }
                            },
                        },
                    },
                    {
                        "name": "get_config",
                        "description": "Get current settings: lang, languages list, etc.",
                        "inputSchema": {"type": "object", "properties": {}, "required": []},
                    },
                    {
                        "name": "set_lang",
                        "description": "Set output language. Show available languages with get_config first.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "lang": {
                                    "type": "string",
                                    "enum": list(LANGUAGES.keys()),
                                }
                            },
                        },
                    },
                    {
                        "name": "set_cycle",
                        "description": "Set cycle query interval in minutes. 0 = off (user queries manually). Use get_config to see current value.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "minutes": {
                                    "type": "integer",
                                    "description": "Cycle interval in minutes (non-negative integer, 0 = off)",
                                    "minimum": 0,
                                }
                            },
                            "required": ["minutes"],
                        },
                    },
                    {
                        "name": "get_cycle",
                        "description": "Get current cycle query interval setting in minutes.",
                        "inputSchema": {"type": "object", "properties": {}, "required": []},
                    },
                    {
                        "name": "set_api_key",
                        "description": "Set and encrypt the DeepSeek API key. Validates the key before saving.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_key": {
                                    "type": "string",
                                    "description": "The DeepSeek API key to save (encrypted on disk)",
                                }
                            },
                            "required": ["session_key"],
                        },
                    },
                ]
            })
        elif method == "tools/call":
            args = params.get("arguments", {})
            name = params.get("name")

            if name == "query_balance":
                cfg, _ = load_config()
                lang = args.get("lang", cfg.get("lang", "en"))
                if lang not in LANGUAGES:
                    lang = "en"
                api_key, err = load_api_key(lang)
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                _, data, err = query_balance(api_key)
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                result = format_balance(data, lang)
                send(mid, {"content": [{"type": "text", "text": result}]})

            elif name == "get_config":
                cfg, err = load_config()
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                cfg["available_languages"] = LANGUAGES
                send(mid, {"content": [{"type": "text", "text": json.dumps(cfg, indent=2, ensure_ascii=False)}]})

            elif name == "set_lang":
                val = args.get("lang")
                if not val or val not in LANGUAGES:
                    avail = ", ".join(LANGUAGES.keys())
                    send(mid, {"content": [{"type": "text", "text": t("lang_unknown", "en", val or "(missing)", avail)}]})
                    continue
                cfg, err = load_config()
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                cfg["lang"] = val
                save_config(cfg)
                send(mid, {"content": [{"type": "text", "text": t("lang_set", val, LANGUAGES[val])}]})

            elif name == "set_cycle":
                minutes = args.get("minutes")
                if not isinstance(minutes, int) or minutes < 0:
                    send(mid, {"content": [{"type": "text", "text": t("cycle_invalid", "en", str(minutes))}]})
                    continue
                cfg, err = load_config()
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                cfg["cycle"] = minutes
                save_config(cfg)
                lang = cfg.get("lang", "en")
                try:
                    manage_cycle_task(minutes, lang)
                except Exception as e:
                    send(mid, {"content": [{"type": "text", "text": f"Config saved but failed to update cron: {e}"}]})
                    continue
                send(mid, {"content": [{"type": "text", "text": t("cycle_set", lang, minutes)}]})

            elif name == "get_cycle":
                cfg, err = load_config()
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                cycle = cfg.get("cycle", 0)
                lang = cfg.get("lang", "en")
                send(mid, {"content": [{"type": "text", "text": t("cycle_get", lang, cycle)}]})

            elif name == "set_api_key":
                session_key = args.get("session_key", "").strip()
                cfg, err = load_config()
                if err:
                    send(mid, {"content": [{"type": "text", "text": f"Error: {err}"}]})
                    continue
                lang = cfg.get("lang", "en")
                if not session_key:
                    send(mid, {"content": [{"type": "text", "text": t("key_missing", lang)}]})
                    continue
                _, data, api_err = query_balance(session_key)
                if api_err:
                    send(mid, {"content": [{"type": "text", "text": t("key_invalid_api", lang, api_err)}]})
                    continue
                save_encrypted(session_key)
                send(mid, {"content": [{"type": "text", "text": t("key_saved", lang)}]})

            else:
                send(mid, error=(-32601, f"Unknown tool: {name}"))

        elif method == "ping":
            send(mid, {})
        elif method in ("notifications/initialized",):
            pass
        else:
            send(mid, error=(-32601, f"Unknown method: {method}"))


if __name__ == "__main__":
    main()
