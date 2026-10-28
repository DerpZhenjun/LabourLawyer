"""Download identified public documents without submitting an application."""
import asyncio,hashlib,re
from pathlib import Path
from urllib.parse import urlsplit

def file_type(body):
    import io,zipfile
    if body.startswith(b'%PDF'):return '.pdf'
    if body.startswith(b'\xd0\xcf\x11\xe0'):return '.doc'
    if body.startswith(b'PK'):
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                if 'word/document.xml' in z.namelist():return '.docx'
                if 'xl/workbook.xml' in z.namelist():return '.xlsx'
        except zipfile.BadZipFile:pass
    return None

async def download_controls(page,folder,controls):
    from portal_audit_capture import official
    out=folder/'attachments';out.mkdir(exist_ok=True)
    for entry in controls[:12]:
        try:
            body=None;url=entry.get('url','')
            if url and official(url):
                try:
                    response=await page.context.request.get(url,timeout=25000)
                    if response.ok:body=await response.body()
                except Exception as exc:
                    # Chrome may support the official site's TLS handshake
                    # when the separate Node request transport does not.
                    entry['request_transport_error']=str(exc)[:180]
            if file_type(body or b'') is None and entry.get('selector'):
                frame=next((f for f in page.frames if f.url==entry.get('frame_url')),page.main_frame)
                target=frame.locator(entry['selector'])
                # Click only the specific detector-tagged document control.
                if not await target.count():continue
                downloads=[];responses=[];tasks=[]
                async def inspect_response(response):
                    if not official(response.url):return
                    content=response.headers.get('content-type','')
                    if not re.search('pdf|officedocument|msword|octet-stream|json',content):return
                    try:
                        data=await asyncio.wait_for(response.body(),10)
                        if len(data)<50*1024*1024:responses.append((response.url,data))
                    except Exception:pass
                def received(response):tasks.append(asyncio.create_task(inspect_response(response)))
                def downloaded(d):downloads.append(d)
                page.on('download',downloaded);page.context.on('response',received);before=set(page.context.pages)
                try:
                    await target.first.click(timeout=4000)
                    for _ in range(10):
                        if downloads:break
                        await page.wait_for_timeout(400)
                    if downloads:
                        download=downloads[0];path=out/'pending-download'
                        await asyncio.wait_for(download.save_as(str(path)),30)
                        body=path.read_bytes();url=download.url
                        # This transient scratch file is replaced by the verified
                        # evidence file, rather than left as a misleading result.
                        path.unlink()
                    fresh=[p for p in page.context.pages if p not in before]
                    for popup in fresh:
                        if body is None and official(popup.url):
                            response=await page.context.request.get(popup.url,timeout=25000)
                            if response.ok:body=await response.body();url=popup.url
                        if file_type(body or b'') is None:
                            # Official preview pages may contain the file in an
                            # iframe or an explicit document download anchor.
                            links=await popup.locator('iframe[src],embed[src],object[data],a[href]').evaluate_all("ns=>ns.map(n=>n.src||n.data||n.href)")
                            for candidate in links:
                                if not official(candidate) or not re.search(r'\.docx?|\.pdf|download|getContent',candidate,re.I):continue
                                response=await page.context.request.get(candidate,timeout=25000)
                                data=await response.body() if response.ok else b''
                                if file_type(data):body=data;url=candidate;break
                        await popup.close()
                    if tasks:await asyncio.gather(*tasks,return_exceptions=True)
                    for candidate,data in responses:
                        if file_type(data):body=data;url=candidate;break
                    if file_type(body or b'') is None:
                        entry['preview_response_urls']=[u for u,_ in responses]
                finally:
                    page.remove_listener('download',downloaded);page.context.remove_listener('response',received)
                    if tasks:await asyncio.gather(*tasks,return_exceptions=True)
            extension=file_type(body or b'')
            if not extension:
                entry['download_status']='no_document_response';continue
            if len(body)>50*1024*1024:raise ValueError('附件超过50MB限制')
            digest=hashlib.sha256(body).hexdigest();name=re.sub(r'[<>:"/\\|?*]','_',entry.get('material_name','官方文书'))[:60]
            path=out/(name+'-'+digest[:10]+extension)
            if not path.exists():path.write_bytes(body)
            entry.update(download_status='downloaded',download_url=url,file=str(path.relative_to(folder)),sha256=digest,bytes=len(body))
        except Exception as exc:entry.update(download_status='failed',download_error=str(exc)[:180])
    return controls
