# 三省劳动仲裁文书试点发布源码

这组文件是试点归档的运行入口。安装版中的 `pilot/start.py` 从用户核对过的归档清单载入锁定的地区、材料、字段合约和填写版。它只在 `127.0.0.1` 提供试点界面与查询、文书生成。下载页面同时显示官方原件和整理后填写版的摘要，并保留各地官方指南入口。

## 构建输入

- 源码依赖按发布审查的文件清单固定。从准确的基础源码获取既有渲染和请求模型，保留每个文件摘要。将本目录运行文件放入归档 `pilot/`，加入项目 `deploy/verify.py` 和锁定依赖 `deploy/requirements.txt`。
- 从干净的确切提交运行 `python deploy/compact_pilot/build_frontend.py --source-revision <完整提交哈希> --output-dir <新目录>`，也可在 npm 缓存齐备时添加 `--offline`。构建在新目录安装锁定依赖，使用试点标志，并将 `frontend-public/` 的文件仅覆盖到隔离前端。回执记录源码、工具版本、构建标志、依赖锁与产物摘要。
- 另行生成经审查的 `data/pilot/` 目录。保留 18 个地区各自的材料、来源、事项版本、文书类型、原件和填写版双摘要、字段合约。将经批准的填写版文件放在 `data/pilot/layouts/`。官方原件、案件资料、独立复核人资料和内部取证产物放在归档之外。
- 独立核对候选的 `DEPLOYMENT-MANIFEST.json`、归档本体和源码版本。把候选归档解压到新目录后才做首次启动，测试用例只使用合成输入。

构建后对 `FRONTEND-RECEIPT.json` 取 SHA-256，使用同一确切提交生成私有归档。<新目录> 必须是此前独立构建的输出目录，<试点数据> 指经审查且带固定清单摘要的数据目录。

```text
python deploy/compact_pilot/package_candidate.py --source-revision <完整提交哈希> --frontend <新目录>/dist --frontend-receipt <新目录>/FRONTEND-RECEIPT.json --frontend-receipt-sha256 <前端回执摘要> --pilot-data <试点数据> --pilot-data-sha256 <数据清单摘要> --output <新归档路径>
```

归档包含项目软件许可 `LICENSE` 和前端依赖声明 `frontend/dist/third-party-notices.txt`。官方空白原件的提供单位通过对应地区的办事指南核对。

## 本机启动与验收

从解压后的归档目录创建外部 Python 3.11 虚拟环境。下例 `python` 需替换为该环境的解释器。

```text
python -m venv ../labourlawyer-pilot-venv
python -m pip install --require-hashes --only-binary=:all: -r deploy/requirements.txt
python -I -B pilot/start.py --manifest-sha256 <已核对的清单摘要> --self-test
python -I -B pilot/start.py --manifest-sha256 <已核对的清单摘要> --port 8093
```

试点入口为 `http://127.0.0.1:8093/pilot-scope.html`。从分发者独立渠道核对归档和清单摘要。发布验收应覆盖两次冷启动、全部地区和文书类型、原件及填写版双摘要、错辖区和旧版本拒绝、实际浏览器下载及 Word 版式。通过 CI 只代表该源码版本的自动检查。发布资产另外检查匿名下载字节和回退记录。

## 源码回归

Windows PowerShell 下先把 `PYTHONPATH` 设为 `backend;deploy/compact_pilot`，Linux 下用 `backend:deploy/compact_pilot`。执行 `python -m unittest discover -s deploy/compact_pilot/tests -p 'test_*.py'` 和 `node --experimental-strip-types scripts/test-pilot-generated-origin.mjs`。正常网页的旧生成来源继续遵循原有响应校验。
