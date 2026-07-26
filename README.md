# LegacyCode — RetroAgent for Windows 3.2

在 Windows 3.2 桌面里获得近似原生的 Claude Code 体验：本机用 QEMU 跑 Win3.2，
通过串口接到 Python Bridge，Bridge 再调用本地 `claude` CLI。

## 第一版目标
在 Win3.2 桌面打开一个串口客户端，逐行向 Claude 提问，实时收到回复，全程中文（GB2312）。

## 架构链路
```
Win3.2 桌面客户端 ──COM1──> QEMU 虚拟串口 ──unix socket──> Python Bridge ──subprocess──> 本机 claude CLI
                                                                                (CLAUDE_CONFIG_DIR → ./claude-home)
```

## 硬约束
- **所有内容局限在本文件夹内**：介质、磁盘镜像、Bridge 代码、claude 配置与会话都在此目录下。
- 不向系统目录写入、不建系统网桥、不改系统配置。
- claude 默认把配置/会话写到 `~/.claude`；用 `CLAUDE_CONFIG_DIR` 重定向到 `./claude-home`。

## 目录（规划）
| 目录 | 用途 |
|------|------|
| `media/` | 下载的 DOS / Win3.2 安装介质 |
| `vm/disks/` | qcow2 磁盘镜像（含 savevm 快照） |
| `vm/sockets/` | unix socket：`com1.sock`（串口）、`qmp.sock`（QMP 控制） |
| `vm/run/` | QEMU 运行时：pid、monitor、日志 |
| `bridge/` | Python Bridge 后端 |
| `claude-home/` | claude 配置/会话重定向目标（`CLAUDE_CONFIG_DIR`） |

## 本机环境（已探查）
- KVM / QEMU 8.2.2（**非 PVE**），无 `vmbr-retro` 网段——Win3.2 走串口，不需要以太网。
- Python 3.12.3 + pip3。
- `/mnt/shared` 为 ext4（`rw,noatime`），478G 可用，支持稀疏文件（qcow2 与快照可用）。
- `claude` CLI 2.1.208（`/home/adam/.nvm/.../bin/claude`）。
- 本机 HTTP 代理 `127.0.0.1:20171`（v2rayA）。

## 调研结论（三块全部完成）

### 1. claude headless 调用
- 命令模板：
  ```
  CLAUDE_CONFIG_DIR=./claude-home claude -p "..." \
      --output-format stream-json \
      --resume <session_id> \
      --add-dir <worktree>
  ```
- 输出为 NDJSON，关键行：`system/init`（含 `session_id`）、`assistant`、`stream_event`、`result`。
- session 恢复：`--resume <session_id>`，跨进程可恢复同一段对话。
- **注意**：具体字段路径据 SDK 推断，实施时需实测，不照抄。

### 2. QEMU + 串口配置（已定型）
- 基础：`-M pc -cpu 486 -m 32 -vga std`，无网无声 `-nic none -audiodev none,id=none`。
- 中文显示：Win3.2 自带 GB2312 字库，标准 VGA 驱动即可——无硬障碍。避免 `bochs-display` / `virtio-vga` / `-cpu max`。
- COM1 → unix socket：`-chardev socket,id=com1,path=<项目内>,server=on,wait=off -serial chardev:com1`。
- QMP 控制：另开 `-chardev socket,id=qmp,... -qmp chardev:qmp`；Python 用 `subprocess.Popen`（不用 `-daemonize`），经 QMP 发 `savevm`/`quit`。
- 磁盘：qcow2 512MB；软盘 `-fda`，换盘用 monitor `change fda`；快照 `savevm/loadvm` 存在 qcow2 内部。

### 3. 介质来源
- **Win3.2 简体中文**：WinWorldPC（12.15MB 软盘，**需注册账号**）或 Archive.org。
- **DOS 底座**：MS-DOS 7.1 CDU ISO（Archive.org，免注册）或 MS-DOS 6.22 软盘（WinWorldPC）。
- 暂无现成「预装 DOS + Win3.2」的硬盘镜像。
- **实际可下性以实测为准**（见下）。

## 推荐执行顺序（自底向上，每层可独立验证）
1. **阶段 1 · Bridge 核心**（纯本机 Linux，最快出成果）：写 Python Bridge——监听 unix socket、解析逐行协议、调 claude CLI（stream-json）、返回文本、session 恢复、UTF-8↔GB2312 编码。用一个本地回环客户端模拟 Win3.2 端，验证 Bridge↔claude 全链路。
2. **阶段 2 · Win3.2 VM**：下载介质 → 建 qcow2 → 装 DOS → 装 Win3.2 → 配 COM1→socket → 存基线快照。
3. **阶段 3 · 端到端**：Win3.2 内用客户端连 COM1，验证「Win3.2 输入 → Bridge → claude → 回复 → Win3.2 显示」与中文 GB2312。

## 待决事项
1. **执行起点**：先做阶段 1（Bridge，快速验证核心）还是先做阶段 2（下介质装 VM）。
2. **Win3.2 客户端**：自写 Win16 串口小程序（Open Watcom，可控但要编译调试）vs 现成终端程序（Terminal.exe 仅 57600；QModem Pro 等难获取）。
3. **介质获取**：以 Archive.org 为主（免注册），若不可直下再请你提供 WinWorldPC 账号或介质。

## 状态
调研全部完成（3/3）。待确认执行起点与客户端选型后正式动手。
