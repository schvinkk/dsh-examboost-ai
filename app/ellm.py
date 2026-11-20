"""ExamBoost 模型接入层：零配置优先，逐级回落，限流自动重试。

通道优先级（先能用的先用，用户什么都不用填）：
  1. 用户自定义配置（设置页手动填写）
  2. 本机 dsh-our-free-model「本地转发」(127.0.0.1:18899 + 落盘 forwardKey)
  3. 本机 dsh-our-free-model 独立服务 (127.0.0.1:18900)
  4. Kilo 匿名网关 —— 无需 Key、无需登录，29 个免费模型，响应快（主力通道）
  5. Pollinations 匿名池 —— 无需 Key，但每 IP 约 45 秒 1 次（备用）

限流处理：429/402 会读取 Retry-After 或退避等待，然后换下一个通道重试，
所以用户看到的效果是"多等几秒但一定能出结果"，而不是报错。
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT_CHAT = 180
TIMEOUT_PROBE = 8
MAX_RETRY_WAIT = 50

KILO_BASE = "https://ai-gateway.kilo.ai/api/v1"
KILO_HEADERS = {
    "http-referer": "https://kilo.ai/",
    "x-title": "ExamBoost",
    "user-agent": "ExamBoost/1.0",
}
KILO_MODELS = ["kilo-auto/free", "openrouter/free", "nvidia/nemotron-3.5-lightning:free"]

ANON_BASE = "https://text.pollinations.ai/v1"
ANON_MODELS = ["openai", "searchgpt"]

# 全局节流：记录每个通道的下次可用时间，避免连续撞限流
_throttle = {"lock": threading.Lock(), "until": {}}


def _wait_ok(pid):
    with _throttle["lock"]:
        return _throttle["until"].get(pid, 0) <= time.time()


def _set_wait(pid, seconds):
    with _throttle["lock"]:
        _throttle["until"][pid] = time.time() + max(0, min(seconds, MAX_RETRY_WAIT))


def _retry_after(headers, default):
    try:
        v = headers.get("Retry-After") if headers else None
        if v:
            return max(1, min(MAX_RETRY_WAIT, int(float(v))))
    except (ValueError, TypeError, AttributeError):
        pass
    return default


def _dsh_home() -> Path:
    return Path(os.environ.get("DSH_HOME") or Path.home() / ".dsh")


def read_ofm_settings():
    """读取 dsh-our-free-model 落盘配置。"""
    p = _dsh_home() / "our-free-model" / "settings.json"
    if not p.exists():
        return None
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    fwd = cfg.get("forward") or {}
    host = fwd.get("host") or "127.0.0.1"
    if not (host.startswith("127.") or host == "localhost"):
        host = "127.0.0.1"
    port = fwd.get("port") or 18899
    return {
        "base_url": f"http://{host}:{port}/v1",
        "key": cfg.get("forwardKey") or "",
        "port": port,
        "enabled": fwd.get("enabled") is True,
    }


def http_json(url, payload=None, headers=None, timeout=TIMEOUT_CHAT):
    """返回 (status, data_or_text, retry_after_seconds)。异常不抛，交调用方回落。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        if v:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(body), 0
            except json.JSONDecodeError:
                return resp.status, body, 0
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:600]
        except OSError:
            pass
        ra = _retry_after(e.headers, 0)
        if not ra:
            m = re.search(r"Retry after (\d+)s", detail)
            if m:
                ra = max(1, min(MAX_RETRY_WAIT, int(m.group(1))))
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = detail
        return e.code, parsed, ra
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", 0


def _friendly(status, msg):
    if status == 0:
        return "连不上（服务未启动或网络不可达）"
    if status in (401, 403):
        return "需要密钥或被拒绝（401/403）"
    if status == 404:
        return "该地址没有对应接口（404）"
    if status in (402, 429):
        return "触发免费额度限流，稍等会自动换通道重试"
    if status >= 500:
        return f"上游服务异常（HTTP {status}）"
    return f"HTTP {status}: {str(msg)[:140]}"


def probe_models(base_url, key="", extra_headers=None):
    url = base_url.rstrip("/") + "/models"
    headers = dict(extra_headers or {})
    if key:
        headers["Authorization"] = f"Bearer {key}"
    status, data, _ = http_json(url, headers=headers, timeout=TIMEOUT_PROBE)
    if status == 200 and isinstance(data, dict):
        ids = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict) and m.get("id")]
        if not ids:
            ids = [m.get("id") for m in (data.get("models") or []) if isinstance(m, dict) and m.get("id")]
        return True, ids[:80], ""
    if status == 200 and isinstance(data, list):
        return True, [str(x.get("id") if isinstance(x, dict) else x) for x in data][:80], ""
    msg = data.get("error") if isinstance(data, dict) else data
    return False, [], _friendly(status, msg)


def discover(custom=None):
    """返回候选通道列表（按优先级），含可用性探测结果。"""
    out = []

    if custom and custom.get("base_url"):
        ok, models, err = probe_models(custom["base_url"], custom.get("api_key", ""))
        out.append({
            "id": "custom", "label": "自定义服务", "desc": custom["base_url"],
            "base_url": custom["base_url"].rstrip("/"), "key": custom.get("api_key", ""),
            "model": custom.get("model", ""), "available": ok, "models": models,
            "error": err, "anon": False, "headers": {}, "weight": 0,
        })

    ofm = read_ofm_settings()
    if ofm:
        ok, models, err = probe_models(ofm["base_url"], ofm["key"])
        out.append({
            "id": "ofm-forward", "label": "本机免费模型（本地转发）",
            "desc": f"dsh-our-free-model 端口 {ofm['port']}" + ("" if ofm["enabled"] else "（转发开关未开）"),
            "base_url": ofm["base_url"], "key": ofm["key"], "model": "",
            "available": ok, "models": models,
            "error": "" if ok else ("请在 DSH 设置 → Our Free Model → 本地转发 打开开关"
                                    if not ofm["enabled"] else err),
            "anon": False, "headers": {}, "weight": 1,
            "switch_hint": not ofm["enabled"],
        })

    base = "http://127.0.0.1:18900/v1"
    ok, models, err = probe_models(base, (custom or {}).get("ofm_standalone_key", ""))
    out.append({
        "id": "ofm-standalone", "label": "本机免费模型（独立服务）", "desc": "端口 18900",
        "base_url": base, "key": (custom or {}).get("ofm_standalone_key", ""), "model": "",
        "available": ok, "models": models, "error": err,
        "anon": False, "headers": {}, "weight": 2,
    })

    # Kilo 匿名网关：主力
    ok, all_models, err = probe_models(KILO_BASE, "", KILO_HEADERS)
    kilo_models = [m for m in all_models if ":free" in m or m.endswith("/free") or "auto" in m][:40] \
        if ok else list(KILO_MODELS)
    out.append({
        "id": "kilo", "label": "Kilo 免费网关（推荐）",
        "desc": "无需登录、无需 Key，29 个免费模型，响应快",
        "base_url": KILO_BASE, "key": "", "model": KILO_MODELS[0],
        "available": True, "models": kilo_models or list(KILO_MODELS),
        "error": "" if ok else f"清单探测失败（仍可直接调用）：{err}",
        "anon": True, "headers": dict(KILO_HEADERS), "weight": 3,
    })

    # Pollinations 备用
    ok2, m2, err2 = probe_models(ANON_BASE, "")
    out.append({
        "id": "anon", "label": "Pollinations 匿名池（备用）",
        "desc": "无需登录；同一网络约 45 秒 1 次，限流时会自动改用 Kilo",
        "base_url": ANON_BASE, "key": "", "model": "openai",
        "available": True, "models": m2 or list(ANON_MODELS),
        "error": "" if ok2 else f"清单探测失败（仍可直接调用）：{err2}",
        "anon": True, "headers": {}, "weight": 4,
    })
    return out


def pick_default(providers):
    for pid in ("ofm-forward", "ofm-standalone", "custom"):
        for p in providers:
            if p["id"] == pid and p["available"]:
                return p
    for p in sorted(providers, key=lambda x: x.get("weight", 9)):
        if p["available"]:
            return p
    return None


def _extract_content(data):
    try:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = (msg.get("content") or "").strip()
        if not content:
            content = (choice.get("text") or "").strip()
        return content
    except (IndexError, AttributeError, TypeError):
        return ""


def chat(base_url, key, model, messages, temperature=0.7, timeout=TIMEOUT_CHAT,
         max_tokens=None, headers=None):
    body = {"model": model or "openai", "messages": messages, "temperature": temperature}
    if max_tokens:
        body["max_tokens"] = int(max_tokens)
    hdr = dict(headers or {})
    if key:
        hdr["Authorization"] = f"Bearer {key}"
    status, data, retry_after = http_json(base_url.rstrip("/") + "/chat/completions",
                                          body, hdr, timeout)
    if status == 200 and isinstance(data, dict):
        content = _extract_content(data)
        if content:
            return True, content, "", 0
        return False, "", "模型返回空内容，可重试或换模型", 0
    msg = data.get("error") if isinstance(data, dict) else data
    if isinstance(msg, dict):
        msg = msg.get("message") or json.dumps(msg, ensure_ascii=False)
    return False, "", _friendly(status, msg), retry_after


def chat_chain(providers, messages, temperature=0.7, timeout=TIMEOUT_CHAT,
               max_tokens=None, retries=1):
    """按优先级尝试；限流则退避后重试同一通道，仍失败就换下一个。

    返回 (ok, 文本, 使用的 provider_id, 错误列表)。
    """
    errors = []
    for p in providers:
        if not p.get("base_url"):
            continue
        pid = p["id"]
        for attempt in range(max(1, retries + 1)):
            if not _wait_ok(pid):
                errors.append(f"{p['label']}：限流冷却中，跳过")
                break
            ok, text, err, retry_after = chat(
                p["base_url"], p.get("key", ""), p.get("model", ""), messages,
                temperature, timeout, max_tokens, p.get("headers"))
            if ok:
                return True, text, pid, errors
            errors.append(f"{p['label']}：{err}")
            # 限流：登记冷却时间，换下一通道（不原地死等，避免用户干等）
            if retry_after:
                _set_wait(pid, retry_after)
                break
            if "空内容" in err and attempt < retries:
                time.sleep(1.2)
                continue
            break
    return False, "", None, errors


def chain_summary(providers):
    """给前端/日志用的一句话说明。"""
    ready = [p["label"] for p in providers if p["available"]]
    return "、".join(ready[:3]) if ready else "无可用通道"
