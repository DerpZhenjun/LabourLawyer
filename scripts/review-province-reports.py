"""Resumeable OpenClaw inspection of actual rendered report pages.

Run with the bundled artifact Python (pypdf). Never starts an Ollama server.
Model findings are retained as opinions pending the maintainer's decisions.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from template_acquisition.openclaw_bridge import describe_image
from terminal_progress import configure, emit

SERVER = 'http://10.66.66.1:11434'
MODEL = 'qwen3.8:27b'
VERSION = 1


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf8')
    temporary.replace(path)


def parse_pages(payload, expected):
    if (payload.get('engine') != 'OpenClaw' or payload.get('base_url') != SERVER
            or payload.get('model') != 'ollama/' + MODEL
            or payload.get('exit_code') != 0 or payload.get('timed_out')
            or not payload.get('completed_output_captured')):
        raise ValueError('Not a completed OpenClaw / Ubuntu result')
    answer = '\n'.join(item.get('text', '') for item in payload['result'].get('outputs', []))
    answer = re.sub(r'^```(?:json)?\s*|\s*```$', '', answer.strip())
    values = json.loads(answer)
    if not isinstance(values, list) or len(values) != len(expected):
        raise ValueError('Model did not return all requested pages')
    if sorted(item.get('page', -1) for item in values) != sorted(expected):
        raise ValueError('Missing, duplicate or unrelated page numbers')
    for item in values:
        if not isinstance(item.get('issues'), list) or not isinstance(item.get('notes'), str):
            raise ValueError('Invalid page findings')
        for issue in item['issues']:
            if (not isinstance(issue, dict) or not isinstance(issue.get('evidence'), str)
                    or not issue['evidence'].strip()
                    or issue.get('severity') not in ('major', 'minor')
                    or not isinstance(issue.get('type'), str)):
                raise ValueError('Invalid issue or missing visible evidence')
    return values


def valid_cache(path, key):
    if not path.is_file():
        return None


    try:
        cached = json.loads(path.read_text('utf8'))
        if cached.get('input_key') != key or cached.get('status') != 'completed':
            return None
        raw = Path(cached['raw_file'])
        if not raw.is_file() or digest(raw) != cached.get('raw_sha256'):
            return None
        pages = parse_pages(json.loads(raw.read_text('utf8')), cached['page_numbers'])
        return cached if pages == cached.get('pages') else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def restore_checked_metadata(state, previous, all_cached):
    def identity(d): return (d.get('document'),d.get('source_sha256'),d.get('pdf_sha256'))
    if (all_cached and previous.get('status')=='completed'
            and [identity(d) for d in state['documents']]==[identity(d) for d in previous.get('documents',[])]):
        for field in ('findings_state','confirmed_report_layout_issues','findings_decisions'):
            if field in previous: state[field]=previous[field]


def review(run, batch_size=4, timeout=300):
    from pypdf import PdfReader
    run = run.resolve()
    if not 1 <= timeout <= 600 or not 1 <= batch_size <= 6:
        raise ValueError('Timeout must be 1..600 seconds and batch size 1..6')
    manifest = json.loads((run / 'render/manifest.json').read_text('utf-8-sig'))
    output = run / 'openclaw-report-check'
    configure(output)
    entries = []
    for document in manifest:
        source, pdf = Path(document['source']), Path(document['pdf'])
        if not source.is_relative_to(run) or not pdf.is_relative_to(run):
            raise ValueError('Report render must belong to this batch')
        if pdf.stat().st_mtime < source.stat().st_mtime:
            raise ValueError('PDF predates its source: render the changed report first')
        reader = PdfReader(str(pdf))
        source_hash, pdf_hash = digest(source), digest(pdf)
        pages = []
        for index, page in enumerate(reader.pages, 1):
            image = pdf.parent / f'page-{index:02}.png'
            if not image.is_file():
                raise ValueError(f'Missing rendered page: {image}')
            pages.append({'page': index, 'image': str(image), 'sha256': digest(image),
                          'text': (page.extract_text() or '')[:1400]})
        entries.append({'document': str(source), 'source_sha256': source_hash,
                        'pdf': str(pdf), 'pdf_sha256': pdf_hash, 'pages': pages})
    state = {'engine': 'OpenClaw', 'model': MODEL, 'model_server': SERVER,
             'review_version': VERSION, 'started_at': datetime.now(timezone.utc).isoformat(),
             'total_pages': sum(len(d['pages']) for d in entries), 'reviewed_pages': 0,
             'documents': [], 'status': 'running', 'findings_state': 'pending_maintainer_decisions'}
    summary = output / 'check.json'
    try: previous=json.loads(summary.read_text('utf8'))
    except (OSError,ValueError): previous={}
    all_cached=True
    save(summary, state)
    emit('report_check',message='检查最终 Word 渲染页',completed=0,total=state['total_pages'],output=str(output))
    for number, document in enumerate(entries, 1):
        target = {'document': document['document'], 'source_sha256': document['source_sha256'],
                  'pdf': document['pdf'], 'pdf_sha256': document['pdf_sha256'], 'pages': []}
        state['documents'].append(target)
        for start in range(0, len(document['pages']), batch_size):
            group = document['pages'][start:start + batch_size]
            expected = [p['page'] for p in group]
            prompt = ('你负责检查最终Word报告实际渲染页，图片按下面页号排序。仅报告明确可见的问题，不要求增加报告内容。'
                      '第一页可为封面，其他页应按省分类。检查：中文标题是否混用奇怪字体、文字/截图是否超出页边界或被裁切、'
                      '空白/损坏图片、标题孤悬与不可读排版。截图自身的网页顶部/底部不完整不等于Word裁切；'
                      '保留截图显示网站错误或未发现结果也是有效证据，不因页面有错误提示便当成排版错误。'
                      '不判断网站是否提供法律服务，不虚构办理步骤；不能仅从文字摘录推断视觉问题。'
                      '如果图片中有清晰矛盾文字可指出，证据不足不猜测。\n'
                      '只返回JSON数组，每页一项，无问题issues=[]：'
                      '[{"page":1,"issues":[{"type":"layout|font|content","severity":"major|minor",'
                      '"evidence":"具体可见位置和问题"}],"notes":"一句检查结论"}]\n'
                      + json.dumps({'document': Path(document['document']).name,
                                    'pages': [{'page': p['page'], 'pdf_text': p['text']} for p in group]}, ensure_ascii=False))
            inputs = {'version': VERSION, 'server': SERVER, 'model': MODEL, 'prompt': prompt,
                      'source_sha256': document['source_sha256'], 'pdf_sha256': document['pdf_sha256'],
                      'pages': [{'page': p['page'], 'sha256': p['sha256']} for p in group]}
            key = hashlib.sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            folder = output / f'document-{number:02}' / key[:20]
            checkpoint = folder / 'review.json'
            cached = valid_cache(checkpoint, key)
            reused = bool(cached)
            all_cached &= reused
            emit('report_check','cached' if reused else 'running',message=Path(document['document']).name+f' / 页 {expected}',output=str(output))
            try:
                if not cached:
                    save(folder / 'inputs.json', inputs)
                    raw = folder / 'openclaw-raw.json'
                    describe_image([Path(p['image']) for p in group], raw, folder / 'runner',
                                   timeout_seconds=timeout, prompt=prompt, role='final_report_page_inspection',
                                   model=MODEL, base_url=SERVER)
                    findings = parse_pages(json.loads(raw.read_text('utf8')), expected)
                    cached = {'input_key': key, 'status': 'completed', 'page_numbers': expected,
                              'pages': findings, 'raw_file': str(raw), 'raw_sha256': digest(raw)}
                    save(checkpoint, cached)
                for page, finding in zip(group, sorted(cached['pages'], key=lambda p: p['page'])):
                    target['pages'].append({**finding, 'image': page['image'], 'sha256': page['sha256'],
                                            'raw_file': cached['raw_file']})
                state['reviewed_pages'] += len(group)
                print(f"OpenClaw {Path(document['document']).name} pages {expected}: completed; "
                      f"{state['reviewed_pages']}/{state['total_pages']}", flush=True)
            except Exception as exc:
                emit('job','incomplete',message='报告检查未完成，保留断点',error=str(exc),output=str(output))
                state.update(status='incomplete', error=str(exc), failed_document=document['document'], failed_pages=expected)
                save(summary, state)
                raise
            save(summary, state)
            emit('report_check',message='本组报告页已检查',completed=state['reviewed_pages'],total=state['total_pages'],output=str(output))
        if digest(Path(document['document'])) != document['source_sha256'] or digest(Path(document['pdf'])) != document['pdf_sha256']:
            state.update(status='incomplete', error='Report changed during inspection')
            save(summary, state)
            raise ValueError(state['error'])
    state.update(status='completed', finished_at=datetime.now(timezone.utc).isoformat())
    state['issue_count'] = sum(len(p['issues']) for d in state['documents'] for p in d['pages'])
    restore_checked_metadata(state,previous,all_cached)
    save(summary, state)
    print(f"Saved {summary}; model findings: {state['issue_count']}", flush=True)
    emit('job','complete',message='报告页面检查完成；意见待核实',completed=state['reviewed_pages'],total=state['total_pages'],counts={'pages':state['reviewed_pages'],'findings':state['issue_count']},output=str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    review(args.run, args.batch_size, args.timeout)
