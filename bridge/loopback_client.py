#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地回环测试客户端 —— 模拟 Win3.2 串口端,连 Bridge 发 ASK、收回复。

不依赖 QEMU / Win3.2,纯本机验证 Bridge↔claude 全链路:
  - 中文 GBK 编解码往返
  - 同一连接多轮提问复用 session(第二轮能记住第一轮的上文)
  - Bridge 的 result 文本提取

用法:
  python3 loopback_client.py "第一句提问" "第二句提问(验证续接)"
  python3 loopback_client.py   # 不带参数则跑默认两轮示例
"""

import socket
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOCKET_PATH = PROJECT_DIR / "vm" / "sockets" / "bridge.sock"
WIRE_ENCODING = "gbk"
REPLY_END_MARK = "__END__"

DEFAULT_PROMPTS = [
    "用一句中文介绍你自己。",
    "我上一句问了你什么?请用一句话简短回答。",  # 验证 session 续接:能答出"介绍你自己"才算通过
]


def ask(sock: socket.socket, prompt: str) -> str:
    """发一行 ASK,阻塞接收直到 REPLY_END_MARK,返回回复正文。"""
    sock.sendall(("ASK " + prompt + "\n").encode(WIRE_ENCODING, errors="replace"))
    buf = b""
    end_bytes = (REPLY_END_MARK + "\n").encode()
    while end_bytes not in buf:
        data = sock.recv(4096)
        if not data:
            break
        buf += data
    text = buf.decode(WIRE_ENCODING, errors="replace")
    return text.split(REPLY_END_MARK)[0].strip()


def main() -> int:
    prompts = sys.argv[1:] or DEFAULT_PROMPTS
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(str(SOCKET_PATH))
    except FileNotFoundError:
        print(f"[client] 找不到 {SOCKET_PATH} —— Bridge 是否已启动?")
        return 1
    print(f"[client] 已连接 {SOCKET_PATH}\n")
    for i, p in enumerate(prompts, 1):
        print(f"── 轮 {i} · 问 ──\n{p}")
        reply = ask(sock, p)
        print(f"── 轮 {i} · 答 ──\n{reply}\n")
    sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
