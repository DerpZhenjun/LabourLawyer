"""Explicit remote-only Ollama configuration; an SSH forward is not a local model."""
from dataclasses import dataclass
import ipaddress,json,os,subprocess,sys,time
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
MODEL='ollama/qwen3.8:27b'
_process_cache={}

@dataclass(frozen=True)
class RemoteConfig:
    endpoint: str
    model: str
    transport: str

def _owned_ssh_tunnel(receipt):
    pid=receipt.get('ssh_pid');port=receipt.get('local_port')
    if not isinstance(pid,int) or not isinstance(port,int):return False
    key=(pid,port);cached=_process_cache.get(key)
    if cached and time.monotonic()-cached[0]<3:return cached[1]
    target=f'127.0.0.1:{port}:127.0.0.1:11434'
    try:
        if sys.platform=='win32':
            script=(f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
                    f"$owners=@(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess; "
                    "[pscustomobject]@{name=$p.Name;command=$p.CommandLine;owners=@($owners)} | ConvertTo-Json -Compress")
            r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=8,creationflags=0x08000000)
            p=json.loads(r.stdout);valid=p.get('name')=='ssh.exe' and target in (p.get('command') or '') and pid in p.get('owners',[])
        else:
            command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
            valid=Path(f'/proc/{pid}/exe').resolve().name=='ssh' and target in command
    except (OSError,ValueError,subprocess.SubprocessError):valid=False
    _process_cache[key]=(time.monotonic(),valid)
    return valid

def _owned_ubuntu_ollama():
    """Explicit colocated Ubuntu deployment; never authorizes a Windows model."""
    if sys.platform!='linux':return False
    try:
        release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        if release.get('ID','').strip('"')!='ubuntu' or release.get('VERSION_ID','').strip('"')!='24.04':return False
        raw=Path(os.environ.get('LABOURLAWYER_UBUNTU_OLLAMA_ROOT',''))
        root=raw.resolve()
        if not raw.is_absolute() or raw!=root or root.name!='Ollama' or root.parent.name!='SJL' or not root.is_relative_to(Path('/home')):return False
        if root.stat().st_uid!=os.getuid():return False
        receipt=json.loads((root/'logs/verification.json').read_text())
        if (not isinstance(receipt,dict) or receipt.get('checks_passed') is not True or receipt.get('root')!=str(root) or receipt.get('model')!='qwen3.8:27b' or receipt.get('listener')!='127.0.0.1:11434'):return False
        pid=int((root/'serve.pid').read_text().strip());proc=Path('/proc')/str(pid)
        if proc.stat().st_uid!=os.getuid() or (proc/'exe').resolve()!=(root/'bin/ollama').resolve():return False
        if b'serve' not in (proc/'cmdline').read_bytes().split(b'\0'):return False
        sockets=set()
        for fd in (proc/'fd').iterdir():
            try:sockets.add(os.readlink(fd))
            except OSError:continue
        for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
            fields=line.split()
            if len(fields)>=10 and fields[1]=='0100007F:'+format(11434,'04X') and fields[3]=='0A' and 'socket:['+fields[9]+']' in sockets:return True
    except (OSError,ValueError,KeyError,TypeError):return False
    return False


def resolve_remote(model=None,api_base=None):
    path=Path(os.getenv('LABOURLAWYER_AI_CONNECTION_FILE',str(ROOT/'.runtime/remote-ai/connection.json')))
    try:receipt=json.loads(path.read_text('utf-8-sig'))
    except (OSError,ValueError):receipt={}
    model=model or os.getenv('LABOURLAWYER_LLM_MODEL') or receipt.get('model') or MODEL
    explicit_endpoint=api_base or os.getenv('OLLAMA_API_BASE')
    transport=os.getenv('LABOURLAWYER_AI_TRANSPORT') or ('direct' if explicit_endpoint else receipt.get('transport') or 'direct')
    endpoint=(explicit_endpoint or receipt.get('endpoint') or '').rstrip('/')
    if not api_base and transport=='ssh' and receipt.get('transport')=='ssh' and receipt.get('verified_remote') is True:
        endpoint=(receipt.get('endpoint') or '').rstrip('/')
    if model!=MODEL:raise ValueError('请配置 Ubuntu Ollama qwen3.8:27b，不能回退本机模型。')
    if transport=='ubuntu-local':
        if endpoint!='http://127.0.0.1:11434' or not _owned_ubuntu_ollama():
            raise ValueError('仅允许已核验的 Ubuntu 24.04 自有 Ollama 进程供同机部署使用；Windows 本机模型始终禁用。')
        return RemoteConfig(endpoint,model,transport)
    try:
        url=urlsplit(endpoint);port=url.port
    except ValueError:raise ValueError('Ubuntu Ollama 远程地址格式无效。') from None
    if (url.scheme not in {'http','https'} or not url.hostname or url.username or url.password
        or url.query or url.fragment or url.path not in {'','/'}):
        raise ValueError('尚未配置 Ubuntu Ollama 远程连接，请运行远程 AI 连接脚本。')
    hostname=url.hostname.lower().rstrip('.')
    local=hostname in {'localhost','localhost.localdomain'} or hostname.endswith('.localhost')
    try:
        address=ipaddress.ip_address(hostname)
        if isinstance(address,ipaddress.IPv6Address) and address.ipv4_mapped:address=address.ipv4_mapped
        local=local or address.is_loopback or address.is_unspecified
    except ValueError:pass
    if local:
        if (url.hostname!='127.0.0.1' or port is None or port==11434 or transport!='ssh'
            or receipt.get('endpoint')!=endpoint or receipt.get('local_port')!=port
            or receipt.get('model')!=MODEL or receipt.get('verified_remote') is not True
            or not _owned_ssh_tunnel(receipt)):
            raise ValueError('Ubuntu Ollama SSH 连接未就绪；禁止使用 Windows 本机模型或未经核验的端口。')
    elif transport!='direct':raise ValueError('Ubuntu Ollama SSH 配置与实际连接地址不一致。')
    return RemoteConfig(endpoint,model,transport)
