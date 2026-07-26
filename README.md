# RetroAgent for Windows 3.2

> 在 1994 年的中文 Windows 3.2 桌面上,和 Claude 对话。

📖 **[项目全文](articles/win3.2-claude.md)** · 📦 **[GitHub](https://github.com/ameriadam12/retroagent-win3.2)**

Windows 3.2 跑不了 Claude Code(没 Node、没网栈),但能让 Claude **住在隔壁**——用一根虚拟串口线把 Win3.2 接到本机的 `claude` CLI:

```
Win3.2 桌面(Terminal.exe) ──COM1──> QEMU 虚拟串口 ──unix socket──> Python Bridge ──subprocess──> claude CLI
```

Win3.2 里敲 `ASK <问题>`,Bridge 调 claude,回复(中文,自动换行)显示在 Terminal。思考时显示 `*Thinking`。

## 快速开始

### 1. clone + 补介质(大文件在 .gitignore 之外,需单独下)
```bash
git clone https://github.com/ameriadam12/retroagent-win3.2.git
cd retroagent-win3.2
mkdir -p media tools vm/sockets vm/run

# DOS 安装光盘(MS-DOS 7.1) + Win3.2 中文版文件树(经 HTTP 代理,如需)
curl -L -o media/dos71cd.iso "https://archive.org/download/dos71cd/dos71cd.iso"
curl -L -o media/win32c.zip "https://archive.org/download/win32c/win32c.zip"

# 可选:Open Watcom(只在你打算重新编译 Win16 客户端时需要)
gh release download Current-build -R open-watcom/open-watcom-v2 -p ow-snapshot.tar.xz
mkdir tools && tar xJf ow-snapshot.tar.xz -C tools
```

仓库里已含一个装好的 `vm/disks/win32.qcow2`(MS-DOS 7.1 + Windows 3.2 + 接好的 COM1),clone 即用,不必自己重装。

### 2. 一键启动
```bash
./start.sh
```
启动 Bridge + QEMU(Win3.2 + VNC `127.0.0.1:5900`)。

### 3. VNC 连上,在 Win3.2 里开 Terminal
```bash
vncviewer 127.0.0.1:5900
```
- `win` 启动 Win3.2(若在 DOS 提示符)
- **File → Run** → `C:\WINDOWS\TERMINAL.EXE`
- **Settings → Communications** → COM1 / 9600 / 8-N-1
- **Settings → Terminal Preferences** → 勾 **Local Echo** + **Line Wrap**
- 敲 `ASK 你好` 回车 → 看到 `*Thinking` + Claude 回复

## 架构

| 组件 | 文件 | 作用 |
|------|------|------|
| Bridge | `bridge/retrobridge.py` | 监听 unix socket,`ASK` 协议,调 `claude -p --output-format stream-json --include-partial-messages`,`*Thinking` 指示 + 完整回复(GBK 编码,自动换行) |
| 回环测试 | `bridge/loopback_client.py` | 本机模拟串口客户端,验证 Bridge↔claude(不依赖 VM) |
| Win3.2 镜像 | `vm/disks/win32.qcow2` | MS-DOS 7.1 + Windows 3.2 中文版,FAT16,COM1 已接 |
| QEMU 读屏 | `vm/qmscreen.py` | QMP send-key + VGA `0xB8000` 文本 dump(GBK 解码),盲操作 DOS 用 |
| CDU 快进 | `vm/ffwd.py` | CDU 安装向导自动过过渡屏 |
| Win16 客户端 | `client-win16/` | Open Watcom 源码(详见下方坑) |
| 启动脚本 | `start.sh` | 一键起 Bridge + QEMU |

## 已知的坑(踩坑实录)

- **QEMU 8.2 send-key 格式变了**:要 `{"keys":[{"type":"qcode","data":"ret"}]}`,旧文档的 `["ret"]` 裸字符串会被静默拒。
- **VGA 文本读屏**:`0xB8000` dump 4000 字节 + GBK 解码,盲操作 DOS/CDU 中文菜单。
- **libguestfs 没root 用不了**(supermin 读 `/boot/vmlinuz` 权限拒绝)→ 改用 mtools `mcopy -i image@@32256` 直接操作 raw 镜像里的 FAT16 分区。
- **Open Watcom Win16 加载崩**:`client-win16/client.exe` 编译成功,但在 Win3.2 中文版 + QEMU 加载即崩(官方 winhello 示例也崩)。工具链兼容性硬伤,改用 Win3.2 自带 Terminal.exe。
- **claude headless**:`CLAUDE_CONFIG_DIR` 重定向会话到项目内;`--include-partial-messages` 才有 `stream_event`(否则只有 system/assistant/result);`stdin=/dev/null` 避免等 stdin 告警。

## 介质来源

| 文件 | 来源 |
|------|------|
| `dos71cd.iso` | [archive.org/dos71cd](https://archive.org/details/dos71cd) — MS-DOS 7.1 CDU 安装光盘 |
| `win32c.zip` | [archive.org/win32c](https://archive.org/details/win32c) — Windows 3.2 中文版已安装文件树 |
| Open Watcom | [github.com/open-watcom/open-watcom-v2](https://github.com/open-watcom/open-watcom-v2) `Current-build` release |

## 文章

完整项目记录(人化版,适合公众号/知乎):**[articles/win3.2-claude.md](articles/win3.2-claude.md)**
