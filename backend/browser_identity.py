"""Use installed Chrome's normal public HTTP identity in an isolated browser.
No certificate overrides, automation hiding or personal browser state changes.
"""
import functools,os,re,subprocess
@functools.lru_cache(maxsize=1)
def normal_user_agent():
    if os.name!='nt':return None
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"(Get-Item -LiteralPath 'C:/Program Files/Google/Chrome/Application/chrome.exe').VersionInfo.ProductVersion"],capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    version=result.stdout.decode('ascii',errors='ignore').strip()
    if result.returncode or not re.fullmatch(r'\d+\.\d+\.\d+\.\d+',version):raise RuntimeError('Cannot confirm installed Chrome version')
    major=version.split('.')[0]
    return f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36'
