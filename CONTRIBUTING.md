# 开发与排查

默认使用方式见 [README](README.md)。本文保留搭建记录与维护工具入口；历史问题不代表已在每个 QEMU 或 Windows 环境下复测。

## Bridge 与客户端

- [bridge/retrobridge.py](bridge/retrobridge.py) 使用 `claude -p --output-format stream-json --verbose --include-partial-messages`，收到完整 `result` 后输出回复。
- Bridge 为 CLI 设置项目内的 `CLAUDE_CONFIG_DIR`，将 stdin 接到 `/dev/null`。会话通过 `--resume` 续接。
- `CLAUDE_BIN` 可覆盖宿主机 CLI 可执行文件路径。
- [bridge/loopback_client.py](bridge/loopback_client.py) 是本机串口模拟工具，但它等待 `__END__\n`，而当前 Bridge 只输出空行分隔；修复协议前不要把该客户端当作能自动结束的验证步骤。
- [client-win16/client.c](client-win16/client.c) 和 [client.def](client-win16/client.def) 保留 Open Watcom 客户端源码。项目曾记录该客户端和官方 winhello 示例加载崩溃，因此默认流程使用系统 Terminal.exe。

## 可选工具链与介质

这些是重新搭建或编译时的来源，不是启动现有镜像的前置条件。

| 资源 | 原项目记录的来源 |
| --- | --- |
| MS-DOS 7.1 CDU 安装光盘 | [archive.org/dos71cd](https://archive.org/details/dos71cd) |
| Windows 3.2 中文版文件树 | [archive.org/win32c](https://archive.org/details/win32c) |
| Open Watcom | [open-watcom/open-watcom-v2](https://github.com/open-watcom/open-watcom-v2) 的 `Current-build` release |

原下载命令保留如下；这些外部资源的当前可下载性未在本轮验证。使用前确认对应介质与工具的使用许可。

```sh
mkdir -p media tools vm/sockets vm/run
curl -L -o media/dos71cd.iso "https://archive.org/download/dos71cd/dos71cd.iso"
curl -L -o media/win32c.zip "https://archive.org/download/win32c/win32c.zip"

# 仅重新编译 Win16 客户端时需要；另需 GitHub CLI。
gh release download Current-build -R open-watcom/open-watcom-v2 -p ow-snapshot.tar.xz
tar xJf ow-snapshot.tar.xz -C tools
```

这只是获取资源，不是完整的镜像安装教程。现有磁盘路径为 `vm/disks/win32.qcow2`。

## QEMU 与磁盘排查记录

- [vm/qmscreen.py](vm/qmscreen.py)：QMP send-key 和 VGA 文本读取工具。项目在 QEMU 8.2 环境记录的按键格式为 `{"keys":[{"type":"qcode","data":"ret"}]}`，旧的 `["ret"]` 格式无法工作。
- VGA 文本记录使用 `0xB8000` 处的 4000 字节并按 GBK 解码，适用于 DOS／CDU 的文本画面。
- [vm/ffwd.py](vm/ffwd.py)：CDU 安装向导过渡屏辅助工具。
- 原环境的 libguestfs／supermin 因读取 `/boot/vmlinuz` 的权限受阻，改用 mtools 操作 raw 镜像。记录中的 `mcopy -i image@@32256` 依赖当时镜像的分区偏移，不能套用于任意磁盘。

## 提交修改

说明修改影响的是串口协议、CLI 调用、VM 启动还是客户端。不要把 Claude 账户状态、会话记录或运行日志带入提交；这些运行目录已由 [.gitignore](.gitignore) 部分排除。

本仓库未提供自动测试套件。README 和本文的相对链接应保持有效；CLI 对话和 VM 操作需要在具备对应依赖的环境中验证，并记录实际结果。
