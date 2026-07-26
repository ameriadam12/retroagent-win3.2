#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDU 安装快进 —— 自动过"过渡屏"(Next/Continue/Create/Reboot),遇到"关键屏"停。

用法: python3 vm/ffwd.py [最大步数]
识别当前 VGA 文本,匹配关键词决定动作:
  - 格式化FAT选择/安装进度/完成/错误  -> STOP(等我决策)
  - Continue+Skip / Create+Quit        -> 按 c
  - Reboot now                          -> 按 r
  - Welcome/intro/agree/path/licence    -> 按 n
  - 其他                                -> 按 n
"""
import socket, json, time, sys

QMP = "/mnt/shared/_Projects/LegacyCode/vm/sockets/qmp.sock"
OUT = "/mnt/shared/_Projects/LegacyCode/vm/run/vga.bin"


def connect():
    s = socket.socket(socket.AF_UNIX); s.settimeout(8)
    s.connect(QMP)
    f = s.makefile("rwb")
    json.loads(f.readline().decode())  # greeting
    f.write(b'{"execute":"qmp_capabilities"}\n'); f.flush(); json.loads(f.readline().decode())
    return s, f


def key(f, k):
    f.write(json.dumps({"execute": "send-key", "arguments": {"keys": [{"type": "qcode", "data": k}]}}).encode() + b"\n")
    f.flush(); json.loads(f.readline().decode())


def screen(f):
    f.write(json.dumps({"execute": "pmemsave", "arguments": {"val": 0xB8000, "size": 4000, "filename": OUT}}).encode() + b"\n")
    f.flush(); json.loads(f.readline().decode())
    data = open(OUT, "rb").read()
    return bytes(bytearray(data[i] for i in range(0, len(data), 2))).decode("gbk", errors="replace")


def classify(text):
    low = text.lower()
    # 关键屏:停下等我
    for kw in ["fat32", "fat16", "fat 32", "format", "installing", "copying",
               "completed", "finished", "error", "fatal", "cannot", "successfully"]:
        if kw in low:
            return ("STOP", kw)
    if "reboot now" in low:
        return ("KEY", "r")
    if "continue" in low and "skip" in low:
        return ("KEY", "c")
    if "create" in low and "quit" in low:
        return ("KEY", "c")
    # 过渡屏
    for kw in ["welcome", "widely-used", "i agree", "obey the following", "licence",
               "destination", "following path", "check the partitions", "strongly recommanded"]:
        if kw in low:
            return ("KEY", "n")
    return ("KEY", "n")


def main():
    max_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    s, f = connect()
    prev_summary = None
    stuck = 0
    for i in range(max_steps):
        text = screen(f)
        lines = [text[r * 80:(r + 1) * 80].rstrip() for r in range(25)]
        visible = [l for l in lines if l.strip()]
        summary = " | ".join(visible[:4])[:95]
        action, kw = classify(text)
        print(f"[{i:2}] {action}({kw}): {summary}")
        if summary == prev_summary:
            stuck += 1
        else:
            stuck = 0
        prev_summary = summary
        if action == "STOP" or stuck >= 2:
            print("=== 停下,当前全画面 ===")
            for r in range(25):
                row = lines[r]
                if row.strip():
                    print(f"{r:2}| {row}")
            break
        key(f, kw)
        time.sleep(2.5)
    s.close()


if __name__ == "__main__":
    main()
