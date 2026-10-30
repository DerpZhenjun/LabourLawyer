# Ubuntu 局域网部署

目标为已授权的 `ubuntu2204` SSH 主机 `192.168.110.81`，应用独占目录 `~/SJL/LabourLawyer`，Python 3.11/3.12。部署仅监听 `192.168.110.81:8088`，使用非 root 用户；不修改防火墙、systemd、Docker 或 `~/SJL/Ollama`。没有域名和 TLS 时，这个 HTTP 地址仅用于可信局域网验收，不能视为公网生产部署。

## 生成可核对的包

先完成当前源码的真实网页构建及后端回归：

```sh
VITE_API_BASE_URL=/ node scripts/client-pipeline.mjs build --targets web,mini
python scripts/ci-backend.py
python scripts/build-deployment-bundle.py --receipt .runtime/client-pipeline/实际运行ID/receipt.json --output .runtime/deployment/LabourLawyer.tar.gz
```

打包器再次执行流水线的 `artifact` 校验，拒绝失败、过期、纳入流水线的源码改变或制品 SHA256 不符的构建回执。`deploy/public-files.json` 逐文件锁定官方模板、公开目录、已批准公开的来源证据和两份客户端目录数据；新增附件须先独立核验，再更新该清单。配置和客户端目录 JSON 使用明确标记的 LF 规范字节，以兼容 Windows/Linux checkout；已封存的官方证据和原件保持原始字节。`deploy/source-files.json` 逐项列出运行源码，新增的本地文件不会因扩展名相同而自动入包。前端仅收录通过构建回执校验的 dist 文件。包内 `DEPLOYMENT-MANIFEST.json` 记录完整路径、长度和 SHA256。

包不会收录 `.git`、`.venv`、`.runtime`、环境文件、个人案件库、账号会话库、上传文书、OpenClaw 私有工作区或模型权重。公开证据路径沿用原目录，避免丢失来源证明链。打包不等于已部署、服务已启动或公网可用。

## 安装隔离环境

在应用用户目录创建独立的 `venv`、`releases/运行标识/` 和 `var/`；先核对传输后 tarball 的 SHA256，再解压到全新的 release 目录。不要在现有 release 上覆盖解压。以下命令使用已核对的本次运行标识替换示例值：

```sh
mkdir -p "$HOME/SJL/LabourLawyer/releases/运行标识"
python3 -m venv "$HOME/SJL/LabourLawyer/venv"
tar -xzf LabourLawyer.tar.gz -C "$HOME/SJL/LabourLawyer/releases/运行标识"
cd "$HOME/SJL/LabourLawyer/releases/运行标识"
"$HOME/SJL/LabourLawyer/venv/bin/python" -m pip install --require-hashes --only-binary=:all: -r deploy/requirements.txt
"$HOME/SJL/LabourLawyer/venv/bin/python" -m pip check
PYTHONDONTWRITEBYTECODE=1 "$HOME/SJL/LabourLawyer/venv/bin/python" deploy/verify.py
```

如果目标系统没有 venv/ensurepip，可使用用户空间 uv 在相同应用目录创建环境；不要为此修改系统 Python 或安装全局依赖。运行所需依赖全部在 `deploy/requirements.txt` 固定版本并校验 hash，不包含模型、GPU、语音和浏览器下载。

## 账号、数据与启动

私人案件、账号会话放在 `var/private/`；公开指南和地区目录放在 `var/public/`。部署 factory 在导入应用前设置全部数据库路径，首次仅将完整校验后的公开快照导入空库；已有公开库不会被覆盖。新账号没有默认密码，不会自动认领旧案件。账号须由本机管理命令或已有管理员创建。

完成差异审查和服务启动授权后，运行：

```sh
bash deploy/run.sh
```

脚本首先核对解压文件清单，然后在前台启动当前 release；已有端口被占用时失败，不终止其他进程。长期进程管理、日志留存和备份需使用应用独占目录，不能把私人库回写进 release 或 Git。保持现有服务版本和私人数据备份后，回退时只切换到已验证的旧 release。

根路径及 Vue 页面路径由同一个 FastAPI 服务提供；已有 API 和 `/health` 保留，未知 `/api/*` 与丢失的脚本仍返回 404。静态路径不能读取隐藏文件、父目录或越界 symlink。

部署 wrapper 在既有 CORS middleware 初始化前，仅额外允许 Windows Electron 使用的 `http://127.0.0.1:有效端口` 来源；保留原生客户端和本机服务的明确来源清单，不允许外部公共来源或通配符。允许跨域不绕过身份认证，未登录的案件接口仍返回 401。

法律助手对话仅在当前标签页保留，按服务和账号隔离；切换身份会关闭对话与数字人窗口。旧浏览器聊天存储保留原字节但不自动加载。数字人页面的新实现仅在当前打开窗口的内存保存对话；数字人服务是独立部署项，配置该服务时也须更新到包含此隐私修复的页面版本。

验收应覆盖手机浏览器从局域网访问、登录/退出、A/B账号隔离、匿名官方文书生成、地区来源绑定、SPA刷新及错误状态。AI 仅连接另行明确配置的既有 Ubuntu Ollama；部署不启动、重配或下载模型。原有政务浏览器采集任务仍依赖 Windows 执行器和 release 相对目录；本部署的对应 POST 保持认证检查，并向管理员明确返回 503，不启动任务、不改写 release。启用前须另行配置和验收应用独占的持久化采集运行环境。OpenClaw 服务回执和 AI 复核仍有各自运行条件，未验收时保持待处理状态。


## 同机 Ubuntu AI（显式启用）

本机Windows始终不运行模型。Ubuntu24.04自身部署可设置 `LABOURLAWYER_ENABLE_UBUNTU_AI=1` 再运行 `deploy/run.sh`；启动器只核对已有`$HOME/SJL/Ollama`安装、安装验收记录、进程UID、可执行文件和11434监听socket，不启动/下载/改配Ollama。失败时拒绝该启用方式，不回退Windows或任意localhost进程。服务状态还会核对Qwen3.8 27B/Q4_K_M。默认未启用AI仍可生成文书。
