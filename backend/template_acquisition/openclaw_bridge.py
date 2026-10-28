from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path
try:
    from terminal_progress import emit, province_from
except ImportError:
    from backend.terminal_progress import emit, province_from


VISION_PROMPT = """你是政务文书采集的视觉复核器。只根据截图可见内容判断，不要猜测隐藏链接。
请输出严格 JSON，字段为：page_kind、service_title、visible_template_names、has_download_action、warnings、confidence。
visible_template_names 只列出截图中明确可见的文书名称；warnings 是字符串数组；confidence 为 0 到 1。
本结果仅用于候选识别，不能批准或覆盖生产模板。"""

DOCUMENT_VISION_PROMPT = """你是官方劳动人事争议文书的视觉复核器。图片由一个或多个带标签的官方文书首页组成。
逐个标签检查并输出严格 JSON，字段为 documents 和 overall_warnings。
documents 是数组，每项字段为 label、visible_title、document_kind、has_blank_fields、layout_intact、warnings、confidence。
document_kind 只能是 application、evidence、combined、guide、unknown 之一；layout_intact 只根据可见的截断、重叠、乱码、缺字判断。
不要补写截图中没有的内容，不要判断法律效力。本结果只做视觉复核，不批准或修改模板。"""

COMPARISON_VISION_PROMPT = """左侧为官方空白模板，右侧为填写后的文书。只检查可见页，不猜测其他页。
填写内容引起自动换行、删去未使用的空白填写行是允许的。检查字体和下划线明显变化、错位、截断或重叠。
签名检查只看“申请人（签名）”“提交人”“接收人”等签署位置是否填了姓名；申请人基本信息的姓名、填写日期、表格内容都不是签名。
无法辨认或本页没有签署位置时填null，不要把日期判为签名。
只输出JSON，字段：issues（每项含位置和可见证据）、signature_filled（true/false/null）、signature_evidence（逐字摘录签署位置的文字）、uncertain。"""


def _completed_model_output(stdout: str, model: str = 'qwen3.8:27b') -> dict | None:
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict):
        return None
    if result.get('ok') is not True or result.get('provider') != 'ollama' or result.get('model') != model:
        return None
    outputs = result.get('outputs')
    if not isinstance(outputs, list) or not any(
        isinstance(item, dict) and isinstance(item.get('text'), str) and item['text'].strip()
        for item in outputs
    ):
        return None
    return result


def write_isolated_config(root: Path, model: str = 'qwen3.8:27b', base_url: str | None = None) -> tuple[Path, dict[str, str]]:
    if model.removeprefix('ollama/') != 'qwen3.8:27b' or base_url not in (None, 'http://10.66.66.1:11434'):
        raise ValueError('本次 Ollama 只允许 Ubuntu http://10.66.66.1:11434 / qwen3.8:27b')
    # The CLI runs from this directory. Relative environment paths would be
    # resolved against it a second time and point at the wrong configuration.
    root = root.resolve()
    state_dir = root / "state"
    workspace_dir = root / "workspace"
    process_temp = root / "temp"
    for directory in (state_dir, workspace_dir, process_temp):
        directory.mkdir(parents=True, exist_ok=True)
    config_path = root / "openclaw.json"
    config = {
        "agents": {
            "defaults": {
                "workspace": str(workspace_dir),
                "model": {"primary": "ollama/qwen3.8:27b"},
                "imageModel": {"primary": "ollama/qwen3.8:27b"},
                "models": {"ollama/qwen3.8:27b": {"params": {
                    "maxTokens": 512, "num_ctx": 4096,
                    "num_predict": 512, "think": False, "temperature": 0,
                }}},
                "modelPolicy": {"allow": ["ollama/qwen3.8:27b"]},
            }
        },
        "plugins": {"entries": {"ollama": {"enabled": True}}},
        "gateway": {
            "mode": "local",
            "bind": "loopback",
            "port": 18809,
            "auth": {"mode": "token", "token": secrets.token_hex(32)},
            "tailscale": {"mode": "off"},
        },
        "browser": {
            "enabled": True,
            "headless": True,
            "noSandbox": False,
            "defaultProfile": "template-acquisition",
            "profiles": {
                "template-acquisition": {
                    "cdpPort": 18810,
                }
            },
        },
        "models": {
            "mode": "merge",
            "providers": {
                "ollama": {
                    "baseUrl": "http://10.66.66.1:11434",
                    "api": "ollama",
                    "apiKey": "ollama-local",
                    "models": [
                        {
                            "id": "qwen3.8:27b",
                            "name": "qwen3.8:27b",
                            "reasoning": True,
                            "input": ["text", "image"],
                            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                            "contextWindow": 8192,
                            "maxTokens": 512,
                            "compat": {"supportsTools": True, "supportsJsonSchemaResponseFormat": True},
                        }
                    ],
                }
            },
        },
        "telemetry": {"enabled": False},
    }
    # Replace the default identifier throughout the isolated configuration.
    config = json.loads(json.dumps(config).replace('qwen3.8:27b', model.removeprefix('ollama/')))
    server='http://10.66.66.1:11434'
    config['models']['providers']['ollama']['baseUrl']=server
    if model == 'qwen3.8:27b':
        # The Ubuntu server owns GPU placement; Windows resource overrides
        # must not force its model onto CPU or constrain its batch size.
        config['agents']['defaults']['models']['ollama/'+model]['params'].update(maxTokens=1024,num_ctx=8192,num_predict=1024)
        config['models']['providers']['ollama']['models'][0]['params']={'num_ctx':8192,'num_predict':1024,'think':False,'temperature':0}
        config['models']['providers']['ollama']['models'][0]['maxTokens']=1024
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "OPENCLAW_STATE_DIR": str(state_dir),
            "OPENCLAW_CONFIG_PATH": str(config_path),
            "OPENCLAW_WORKSPACE_DIR": str(workspace_dir),
            "OPENCLAW_BROWSER_HEADLESS": "1",
            "OLLAMA_API_KEY": "ollama-local",
            "TEMP": str(process_temp.resolve()),
            "TMP": str(process_temp.resolve()),
        }
    )
    return config_path, env


def describe_image(
    screenshot: Path | list[Path],
    output: Path,
    root: Path,
    timeout_seconds: int = 180,
    prompt: str = VISION_PROMPT,
    role: str = "candidate_visual_review_only",
    model: str = 'qwen3.8:27b',
    base_url: str | None = None,
) -> Path:
    root = root.resolve()
    if not 1<=timeout_seconds<=600:raise ValueError('Model timeout must be between 1 and 600 seconds')
    executable = shutil.which("openclaw") or shutil.which("openclaw.cmd")
    # Keep executable discovery local to this call; do not mutate process PATH.
    configured = os.getenv('OPENCLAW_EXECUTABLE')
    if configured and Path(configured).is_file():
        executable = configured
    if not executable and os.name == 'nt':
        installed = Path(r'D:\OpenClaw\npm-global\openclaw.cmd')
        if installed.is_file():
            executable = str(installed)
    if not executable:
        raise FileNotFoundError("OpenClaw CLI is not installed or not on PATH")
    model = model.removeprefix('ollama/')
    _, env = write_isolated_config(root, model, base_url)
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Bypass the npm .cmd wrapper when its actual launcher is available.
    # This also gives timeout handling a direct Node process to terminate.
    launcher=Path(executable).parent/'node_modules'/'openclaw'/'openclaw.mjs'
    node=shutil.which('node')
    prefix=[node,str(launcher)] if node and launcher.is_file() else [executable]
    command = [
        *prefix,
        "infer", "model", "run", "--local",
        "--model", "ollama/" + model,
        "--thinking", "off",
        "--prompt", prompt,
        "--json",
    ]
    screenshots=screenshot if isinstance(screenshot,list) else [screenshot]
    for path in screenshots:
        command.extend(['--file',str(path.resolve())])
    progress = dict(call_id=str(output.resolve()), province=province_from(screenshots),
                    timeout_seconds=timeout_seconds, output=str(output.parent), engine='OpenClaw')
    emit('model','waiting',message='OpenClaw 已向 Ubuntu Qwen 发送请求',**progress)
    def decode_console(data: bytes) -> str:
        for encoding in ("utf-8", "gb18030"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
            command,
            cwd=str(root),
            env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            creationflags=creation_flags,
        )
    try:
        stdout,stderr=process.communicate(timeout=timeout_seconds)
        completed=subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    except KeyboardInterrupt:
        emit('model','failed',message='本次模型调用已中断',**progress)
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=creation_flags,timeout=15)
        else:process.kill()
        raise
    except subprocess.TimeoutExpired as exc:
        emit('model','failed',message='Ubuntu 模型请求超时',error=f'超过 {timeout_seconds} 秒',**progress)
        # Killing only cmd.exe leaves its Node child holding capture pipes open.
        # Terminate our own process tree so timeout really is bounded.
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=creation_flags,timeout=15)
        else:process.kill()
        try:stdout,stderr=process.communicate(timeout=10)
        except subprocess.TimeoutExpired:stdout,stderr=exc.stdout or b'',exc.stderr or b''
        captured_stdout = decode_console(stdout or b"")
        parsed_stdout = _completed_model_output(captured_stdout, model)
        completed_output = parsed_stdout is not None
        payload = {
            "engine": "OpenClaw",
            "model": "ollama/" + model,
            "base_url": 'http://10.66.66.1:11434',
            "exit_code": None,
            "timed_out": True,
            "completed_output_captured": completed_output,
            "timeout_seconds": timeout_seconds,
            "stdout": captured_stdout,
            "stderr": decode_console(stderr or b""),
            "role": role,
        }
        if parsed_stdout is not None:
            payload['result'] = parsed_stdout
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError(f"OpenClaw vision timed out; see {output}") from exc
    payload = {
        "engine": "OpenClaw",
        "model": "ollama/" + model,
        "base_url": 'http://10.66.66.1:11434',
        "exit_code": completed.returncode,
        "timed_out": False,
        "stdout": decode_console(completed.stdout),
        "stderr": decode_console(completed.stderr),
        "role": role,
    }
    result = _completed_model_output(payload["stdout"], model)
    payload["completed_output_captured"] = result is not None
    if result is not None:
        payload["result"] = result
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if completed.returncode != 0:
        emit('model','failed',message='OpenClaw 模型调用失败',error=f'exit {completed.returncode}',**progress)
        raise RuntimeError(f"OpenClaw vision failed; see {output}")
    if not payload["completed_output_captured"]:
        emit('model','failed',message='OpenClaw 未返回完整模型结果',**progress)
        raise RuntimeError(f"OpenClaw returned no completed model output; see {output}")
    emit('model','completed',message='OpenClaw 收到完整 Ubuntu 模型结果',**progress)
    return output
