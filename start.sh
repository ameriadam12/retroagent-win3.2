#!/bin/bash
# RetroAgent 一键启动:Bridge + QEMU(Win3.2 + COM1 串口 + VNC)
# 用法: ./start.sh
# 停止: QEMU 窗口关闭 / Ctrl+C,Bridge 自动停
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
mkdir -p vm/sockets vm/run

export CLAUDE_CONFIG_DIR="$DIR/claude-home"

echo "[start] 启动 Bridge..."
rm -f vm/sockets/bridge.sock
python3 bridge/retrobridge.py > vm/run/bridge.log 2>&1 &
BRIDGE_PID=$!
sleep 1

echo "[start] 启动 QEMU (Win3.2, VNC 127.0.0.1:5900)..."
qemu-system-x86_64 -M pc -cpu 486 -m 64 \
  -hda "$DIR/vm/disks/win32.qcow2" -boot c -vga std \
  -vnc 127.0.0.1:0 \
  -chardev socket,id=com1,path="$DIR/vm/sockets/bridge.sock",reconnect=1 \
  -serial chardev:com1 \
  -chardev socket,id=qmp,path="$DIR/vm/sockets/qmp.sock",server=on,wait=off \
  -qmp chardev:qmp 2> vm/run/qemu.log &
QEMU_PID=$!

echo ""
echo "==============================================="
echo " RetroAgent 已启动"
echo "   VNC:      vncviewer 127.0.0.1:5900"
echo "   Bridge:   vm/run/bridge.log"
echo "==============================================="
echo "Win3.2 里:开 Terminal.exe (File→Run C:\\WINDOWS\\TERMINAL.EXE)"
echo "  Settings→Communications→COM1/9600/8N1"
echo "  Settings→Terminal Preferences→Local Echo + Line Wrap"
echo "  敲: ASK <你的问题>  回车"
echo ""
echo "Ctrl+C 停止..."

trap "kill $QEMU_PID $BRIDGE_PID 2>/dev/null; exit" INT TERM
wait $QEMU_PID
kill $BRIDGE_PID 2>/dev/null
