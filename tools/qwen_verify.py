"""Bounded, read-only second-model review using the Ubuntu Ollama server."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys

BASE_URL='http://10.66.66.1:11434'
MODEL='qwen3.8:27b'

def request(path,payload=None,timeout=30):
    if not 1<=timeout<=600:raise ValueError('Timeout must be between 1 and 600 seconds')
    command=['curl.exe','--silent','--show-error','--fail-with-body','--noproxy','10.66.66.1','--connect-timeout','10','--max-time',str(timeout),BASE_URL+path]
    body=None
    if payload is not None:
        command+=['--header','Content-Type: application/json','--data-binary','@-']
        body=json.dumps(payload,ensure_ascii=False).encode('utf8')
    response=subprocess.run(command,input=body,capture_output=True,timeout=timeout+5,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    if response.returncode:raise RuntimeError(f'Ubuntu Ollama request failed ({response.returncode}): '+response.stderr.decode('utf8',errors='replace')[:600]+' '+response.stdout.decode('utf8',errors='replace')[:600])
    return json.loads(response.stdout.decode('utf8'))

def verify(prompt,images=(),timeout=600,max_tokens=1200):
    models=request('/v1/models',timeout=30)
    if MODEL not in [m.get('id') for m in models.get('data',[])]:raise RuntimeError('Ubuntu server does not list '+MODEL)
    content=[{'type':'text','text':prompt}]
    for path in images:
        content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode('ascii')}})
    response=request('/v1/chat/completions',{'model':MODEL,'messages':[{'role':'system','content':'你是独立复核者。依据提供的真实代码、证据与测试结果分析。引用具体代码或证据；不修改文件，不编造未提供的信息。'},{'role':'user','content':content}],'temperature':0,'max_tokens':max_tokens,'stream':False,'reasoning_effort':'none'},timeout=timeout)
    if response.get('model')!=MODEL:raise RuntimeError('Unexpected response model: '+str(response.get('model')))
    answer=response.get('choices',[{}])[0].get('message',{}).get('content')
    if not isinstance(answer,str) or not answer.strip():raise RuntimeError('Remote model returned no text')
    return {'base_url':BASE_URL,'model':MODEL,'response':response,'answer':answer}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--context',type=Path,required=True);parser.add_argument('--image',action='append',type=Path,default=[]);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--timeout',type=int,default=600);args=parser.parse_args()
    result=verify(args.context.read_text(encoding='utf8'),args.image,args.timeout)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(result['answer'],flush=True)
