#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QEMU 屏幕交互辅助 —— 发按键、等待、读 VGA 文本屏幕(0xB8000, 80x25, GBK 解码)。

用法:
  python3 vm/qmscreen.py [sleep秒] [key1 key2 ...]
  例:
    python3 vm/qmscreen.py 2 ret          # 按 Enter,等2秒,读屏
    python3 vm/qmscreen.py 1.5 tab ret    # Tab 后 Enter
    python3 vm/qmscreen.py 2 y            # 按 Y
    python3 vm/qmscreen.py 2              # 不按键,仅等2秒读屏

键名(ret/tab/esc/spc/up/down/left/right/y/n/数字/字母...)直接作为参数;
首个纯数字参数被当作等待秒数,其余当按键。不传按键则只读屏。
"""
import socket, json, sys, time

QMP = "/mnt/shared/_Projects/LegacyCode/vm/sockets/qmp.sock"
OUT = "/mnt/shared/_Projects/LegacyCode/vm/run/vga.bin"

# 常见键名归一化到 QMP send-key 的键名
KEYMAP = {
    "enter": "ret", "return": "ret", "ret": "ret", "\n": "ret",
    "tab": "tab", "esc": "esc", "escape": "esc",
    "space": "spc", "spc": "spc", " ": "spc",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "pgup": "pgup", "pgdn": "pgdn",
    "ins": "insert", "insert": "insert", "del": "delete", "delete": "delete",
    "bs": "backspace", "backspace": "backspace",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f10": "f10",
    "y": "y", "n": "n",
}


def main():
    sleep_s = 1.5
    keys = []
    for a in sys.argv[1:]:
        if a.replace(".", "", 1).isdigit():
            sleep_s = float(a)
        else:
            keys.append(a)

    s = socket.socket(socket.AF_UNIX); s.settimeout(8)
    s.connect(QMP)
    f = s.makefile("rwb")

    def obj():
        return json.loads(f.readline().decode())

    obj()  # greeting
    f.write(b'{"execute":"qmp_capabilities"}\n'); f.flush(); obj()

    for k in keys:
        qk = KEYMAP.get(k.lower(), k.lower())
        f.write(json.dumps({"execute": "send-key", "arguments": {"keys": [{"type": "qcode", "data": qk}]}}).encode() + b"\n")
        f.flush(); obj(); time.sleep(0.05)

    time.sleep(sleep_s)

    f.write(json.dumps({"execute": "pmemsave", "arguments": {"val": 0xB8000, "size": 4000, "filename": OUT}}).encode() + b"\n")
    f.flush(); obj()
    s.close()

    data = open(OUT, "rb").read()
    chars = bytearray(data[i] for i in range(0, len(data), 2))
    text = bytes(chars)
    for r in range(25):
        row = text[r * 80:(r + 1) * 80].decode("gbk", errors="replace").rstrip()
        if row.strip():
            print(f"{r:2}| {row}")


if __name__ == "__main__":
    main()
