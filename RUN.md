# 启动、停止与系统边界

## 本期测了什么

| 环境 | 状态 |
| --- | --- |
| macOS 26.5 / Apple M4 / CPU 两线程 | 两种用途各两份输入、真实输出、结构化逐字段核对、摘要人工事实复核；服务重启和停止已测 |
| Windows ARM64 | 按官方0.40.13的ARM64 CLI包准备入口；未核心实测 |
| Windows Intel/AMD x64 | 需现有官方CLI并传入路径；未核心实测 |
| Linux | 需现有官方CLI并传入路径；未核心实测；本期未提交shenji作业 |

macOS入口测试复用了本轮单独下载且校验的官方压缩包，在空模型目录完成真实模型下载。此前的人工准入也单独验证了同一版本下载、模型获取及CPU推理；不声称在全新系统完成了Python安装。

## macOS

安装 Python 3.9 或更新版本后，在仓库目录执行 `bash start.sh`。脚本使用 curl 从官方 GitHub Release 下载固定0.40.13包，核对SHA256后解压到 `.runtime/bundle/`。模型下载到 `.runtime/models/`，默认只监听 `127.0.0.1:11439`，不向局域网开放。

首次 Ollama 服务启动会在 `~/.ollama/` 生成 `id_ed25519` 与公钥，这是官方CLI的行为。本练习不读取或分发这些文件，不改变 HOME、不关闭系统安全保护、不配置登录启动项。日志 `output/service.log` 可能有本机路径或公钥信息，**不要整份公开上传**。

模型通过官方pull接口下载，并核对本期清单摘要：

```text
Ollama: 0.40.13
模型: qwen3:0.6b / Q4_K_M
模型manifest: 7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435
GGUF层: 7f4030143c1c477224c5434f8272c662a8b042079a0a584f0a27a1684fe2e1fa
```

本期请求设 `num_gpu=0`、`num_thread=2`、上下文2048、温度0。`output/verification.json` 中 `loaded.models[].size_vram=0` 是本次CPU路径的核对点。模型选小只为降低本机试用成本，不代表回答能力等于大模型。

## Windows

Python 3.9+ 和 curl 可用后，Windows ARM64可运行 `start.cmd`。入口下载官方ARM64 ZIP并核SHA，未在本期虚拟机实际跑过，因此遇到失败先保存现象，不当成已兼容。

Windows x64请从[官方发布页](https://github.com/ollama/ollama/releases/tag/v0.40.13)下载对应CLI包，解压后运行：

```powershell
py -3 start.py --ollama-bin "C:\your-path\ollama.exe"
```

这只是官方路径与本练习参数说明；没有以ARM64入口代替x64实测。不要因为系统提示而关闭SmartScreen、杀毒或签名检查；需要本人确认的系统提示应由本人处理。

## Linux

从[官方Linux说明](https://docs.ollama.com/linux)准备0.40.13官方CLI，再执行：

```sh
python3 start.py --ollama-bin /your-path/ollama
```

同机已有全局Ollama服务时仍只用本练习的11439端口；不要结束他人的服务。此命令尚未在shenji核心实测，不声称Linux已通过。

## 结果和停止

正常结束会显示“完成”和“本入口启动的Ollama服务已停止”。`output/verification.json` 保存结构化样例比较和卸载后模型列表。摘要必须由人对照输入确认对象、日期、限制词以及计划/取消状态。

运行中按一次 Ctrl+C，入口的 `finally` 会尝试停止自己启动的服务。不要把关闭终端当作任意情况下都已停止；可在浏览器打开 `http://127.0.0.1:11439/api/version` 检查。正常结束后应连接失败；若仍有服务，先核对进程归属，不盲目结束。

重跑会覆盖 `output/` 中同名结果和日志。想保留对照先复制结果目录，`.runtime/` 则是可复用下载缓存。本入口检测到11439已有服务会直接停止，不抢占端口，也不复用权属不明的服务。

软件包下载预算240秒，模型pull等待240秒，单次生成等待100秒。网络超时会退出并停止本入口的服务；保留已完成的文件，不把超时说成模型回答质量失败。
