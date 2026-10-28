"""Read-only diagnostics and a real, isolated OpenClaw image smoke check."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.runtime' / 'launch-center'


def get_json(url: str):
    with urlopen(url, timeout=4) as response:
        return json.load(response)


def model_check(model='qwen3.8:27b') -> dict:
    if model!='qwen3.8:27b':raise ValueError('当前仅使用 Ubuntu qwen3.8:27b')
    server='http://10.66.66.1:11434'
    try:
        models = get_json(server+'/api/tags')['models']
    except Exception as exc:
        raise RuntimeError(f'Ollama {server} 未响应：{exc}；不会切换到其他服务器或下载模型。') from exc
    names = [item.get('name', '') for item in models]
    if model not in names:
        raise RuntimeError(f'{server} 缺少 {model}。已安装：{names}；这里不会自动拉取模型。')
    executable = shutil.which('openclaw') or shutil.which('openclaw.cmd')
    if not executable:
        raise RuntimeError('OpenClaw 不在 PATH 中；可在 scripts/launcher/settings.local.json 指定 openclawCommand。')
    result = {'ollama_reachable': True, 'required_model_installed': True,
              'model': 'ollama/'+model, 'base_url':server, 'openclaw': executable,
              'note': '这只是依赖检查；start.bat openclaw-smoke（QUALITY → AI CONNECT）才实际发送图像。'}
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


def health() -> int:
    tools = {name: shutil.which(name) for name in ('node', 'npm.cmd', 'uv', 'adb', 'openclaw.cmd')}
    services = {}
    for name, url in {'backend': 'http://127.0.0.1:8000/health', 'web': 'http://127.0.0.1:5173',
                      'ollama': 'http://10.66.66.1:11434/api/version', 'digital_human': 'http://127.0.0.1:3000'}.items():
        try:
            with urlopen(url, timeout=2) as response:
                services[name] = {'url': url, 'reachable': response.status == 200}
        except Exception as exc:
            services[name] = {'url': url, 'reachable': False, 'error': str(exc)}
    try:
        vision = model_check()
    except Exception as exc:
        vision = {'ready': False, 'error': str(exc)}
    sys.path.insert(0, str(ROOT / 'backend'))
    from province_documents import PROVINCE_DOCUMENTS
    enabled = [p for p in PROVINCE_DOCUMENTS.values() if p.get('documents')]
    payload = {'checked_at': datetime.now().astimezone().isoformat(), 'python': sys.executable,
               'tools': tools, 'services': services, 'vision': vision,
               'available_regions': len(enabled), 'document_types': sum(len(p['documents']) for p in enabled),
               'local_docx_files': len(list((ROOT / 'templates' / '_docx').rglob('*.docx'))),
               'cache': {k: os.environ.get(k) for k in ('TEMP', 'UV_CACHE_DIR', 'NPM_CONFIG_CACHE', 'HF_HOME')},
               'note': '服务未启动不代表安装失败；本检查不启动服务、不安装、不下载。'}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / 'environment-check.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f'检查结果：{path}')
    return 0


def vision_smoke() -> int:
    model_check()
    candidates = sorted((ROOT / 'templates' / '_validation' / 'generated-documents').glob('jiangsu/application/comparison-*.png'))
    if not candidates:
        candidates = sorted((ROOT / 'templates' / '_validation' / 'generated-documents').rglob('comparison-*.png'))
    if not candidates:
        raise RuntimeError('没有现成对比截图。请先运行 start.bat examples（QUALITY → EXAMPLES）。')
    spec = importlib.util.spec_from_file_location('launch_openclaw_bridge', ROOT / 'backend/template_acquisition/openclaw_bridge.py')
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    run = OUTPUT / 'openclaw-smoke' / datetime.now().strftime('%Y%m%d-%H%M%S')
    print(f'实际发送图像：{candidates[0]}\n模型：ollama/qwen3.8:27b；最多等待 240 秒。\n结果目录：{run}', flush=True)
    result = bridge.describe_image(candidates[0], run / 'response.json', run / 'isolated',
                                   timeout_seconds=240, prompt=bridge.COMPARISON_VISION_PROMPT,
                                   role='launch_center_real_image_smoke')
    print(f'已收到模型完整输出：{result}。这是连接测试，不是全省复核完成。', flush=True)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['health', 'model-check', 'vision-smoke', 'audit-result', 'audit-inputs'])
    parser.add_argument('--province')
    parser.add_argument('--model',default='qwen3.8:27b')
    args = parser.parse_args()
    try:
        if args.action == 'model-check':
            model_check(args.model)
        elif args.action == 'vision-smoke':
            raise SystemExit(vision_smoke())
        elif args.action in ('audit-result', 'audit-inputs'):
            tasks = json.loads((ROOT / 'templates/_validation/generated-documents/manifest.json').read_text(encoding='utf-8'))
            if args.province:
                tasks = [t for t in tasks if t['slug'] == args.province]
            if not tasks:
                raise RuntimeError('没有所选地区的生成案例。请核对地区 slug，并先运行 start.bat examples。')
            if args.action == 'audit-inputs':
                for task in tasks:
                    source = Path(task['template'])
                    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != task.get('template_sha256'):
                        raise RuntimeError(f'{task["slug"]} 模板已变化，请重新运行 start.bat examples 再做图像复核。')
                    if not task.get('generated_pages') or not task.get('comparisons') or any(not Path(p).is_file() for p in task['comparisons']):
                        raise RuntimeError(f'{task["slug"]} 没有完整对比截图，请先运行 start.bat examples。')
                print(f'已核对 {len(tasks)} 份生成案例的模板版本和截图。')
                raise SystemExit(0)
            problems = [(t['slug'], t['kind']) for t in tasks if any(k.endswith('_render_error') for k in t)
                        or any(v.get('error') or (v.get('skipped') and '连续两次' in v['skipped']) for v in t.get('vision', []))]
            if problems:
                raise RuntimeError(f'存在未完成的渲染或视觉调用：{problems}；查看 manifest.json。模型意见仍需人工审阅。')
            print('未发现记录中的渲染/调用错误；这不代表模型意见无问题或所有页已审阅。')
        else:
            raise SystemExit(health())
    except Exception as exc:
        print(str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
