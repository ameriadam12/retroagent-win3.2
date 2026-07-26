#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RetroAgent Bridge(非流式 + Thinking 指示版) —— 串口端逐行问答。

行为:
  - 收到 ASK 后,先回显 "> ASK ..." 确认。
  - claude 思考阶段(thinking_delta)显示 "*Thinking"。
  - 取消流式:text_delta 不实时推,等 claude 完整 result 后一次性输出(自动换行)。
"""

import json
import os
import socket
import subprocess
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLAUDE_HOME = PROJECT_DIR / "claude-home"
SOCKET_PATH = PROJECT_DIR / "vm" / "sockets" / "bridge.sock"
WORKDIR = PROJECT_DIR
WIRE_ENCODING = "gbk"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
CLAUDE_TIMEOUT = 300
WRAP_WIDTH = 78


def wrap_text(text, width=WRAP_WIDTH):
    """按宽度软换行,段落(已有 \n)内超宽插 \r\n。"""
    out = []
    for para in text.split("\n"):
        para = para.rstrip("\r")
        if len(para) <= width:
            out.append(para)
            continue
        for i in range(0, len(para), width):
            out.append(para[i:i + width])
    return "\r\n".join(out)


def call_claude(prompt, session_id, conn):
    """调 claude:思考时显示 *Thinking,完成后一次性输出完整回复(自动换行)。
       返回 (新 session_id, 是否出错)。"""
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_HOME)
    cmd = [CLAUDE_BIN, "-p", prompt, "--output-format", "stream-json",
           "--verbose", "--include-partial-messages"]
    if session_id:
        cmd += ["--resume", session_id]
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(WORKDIR), env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        conn.sendall(b"[claude not found]\r\n")
        return session_id, True

    sid = session_id
    showed_thinking = False
    full_text = ""
    err_msg = ""
    broken = False
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            if t == "system" and d.get("subtype") == "init":
                sid = d.get("session_id") or sid
            elif t == "stream_event":
                ev = d.get("event") or {}
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta") or {}
                    # 思考阶段:显示一次 *Thinking 指示
                    if delta.get("type") == "thinking_delta" and not showed_thinking:
                        try:
                            conn.sendall(b"*Thinking\r\n")
                        except (BrokenPipeError, ConnectionResetError):
                            broken = True
                            break
                        showed_thinking = True
                    # text_delta 不实时推(取消流式)
            elif t == "result":
                sid = d.get("session_id") or sid
                if d.get("is_error"):
                    r = d.get("result")
                    err_msg = (r.get("message") if isinstance(r, dict) else str(r)) or "claude error"
                else:
                    full_text = d.get("result") or ""
        proc.wait(timeout=CLAUDE_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            conn.sendall(b"\r\n[timeout]\r\n")
        except Exception:
            pass
        return sid, True

    if broken:
        return sid, False

    try:
        if showed_thinking:
            conn.sendall(b"\r\n")  # *Thinking 与回复之间空一行
        if full_text:
            conn.sendall((wrap_text(full_text) + "\r\n").encode(WIRE_ENCODING, errors="replace"))
        elif err_msg:
            conn.sendall(("[error] " + err_msg + "\r\n").encode(WIRE_ENCODING, errors="replace"))
            return sid, True
    except (BrokenPipeError, ConnectionResetError):
        pass
    return sid, False


def handle_client(conn):
    conn.settimeout(600)
    session_id = None
    buf = b""
    try:
        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            if not data:
                break
            buf += data
            while True:
                ir = buf.find(b"\r")
                inl = buf.find(b"\n")
                idx = min((i for i in (ir, inl) if i >= 0), default=-1)
                if idx < 0:
                    break
                raw = buf[:idx]
                buf = buf[idx + 1:]
                line = raw.decode(WIRE_ENCODING, errors="replace").strip()
                if not line:
                    continue
                try:
                    conn.sendall(("> " + line + "\r\n").encode(WIRE_ENCODING, errors="replace"))
                except (BrokenPipeError, ConnectionResetError):
                    return
                print(f"[Bridge] 收到: {line[:100]}", flush=True)

                up = line.upper()
                if up.startswith("ASK "):
                    prompt = line[4:].strip()
                    if not prompt:
                        conn.sendall(b"[ASK needs question]\r\n")
                        continue
                    conn.sendall(b"\r\n")
                    sid, is_err = call_claude(prompt, session_id, conn)
                    session_id = sid
                    conn.sendall(b"\r\n")  # 回复结束分隔
                elif up in ("HELLO", "PING"):
                    conn.sendall(b"PONG RetroAgent/1\r\n")
                elif up in ("BYE", "QUIT", "EXIT"):
                    conn.sendall(b"[bye]\r\n")
                    return
                else:
                    conn.sendall(("[unknown] " + line + "  (use: ASK <question>)\r\n").encode(WIRE_ENCODING, errors="replace"))
    except Exception as e:
        try:
            conn.sendall(("[bridge error] " + str(e) + "\r\n").encode(WIRE_ENCODING, errors="replace"))
        except Exception:
            pass
    finally:
        conn.close()


def main():
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(SOCKET_PATH))
    srv.listen(4)
    print(f"[Bridge] 监听 {SOCKET_PATH}  (非流式+Thinking指示, 编码={WIRE_ENCODING}, 换行宽={WRAP_WIDTH})")
    print("[Bridge] 协议: 一行 'ASK <提问>' 即可;Ctrl+C 退出。")
    try:
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[Bridge] 退出。")
    finally:
        srv.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()


if __name__ == "__main__":
    main()
