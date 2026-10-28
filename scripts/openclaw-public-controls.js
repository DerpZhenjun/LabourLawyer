() => {
  const documents=[document];
  for(const frame of document.querySelectorAll('iframe')){
    try { if(frame.contentDocument && new URL(frame.src,location.href).hostname.endsWith('.gov.cn')) documents.push(frame.contentDocument) } catch{}
  }
  const marked=[];
  // A labour keyword in search history is not a matching service result.
  // Preserve its actual context in the name used by the browser planner.
  for(const doc of documents) for(const node of doc.querySelectorAll('a,button,[role=button]')){
    const text=(node.innerText||'').trim();
    if(!/^(劳动仲裁|劳动人事争议仲裁|劳动人事争议调解)$/.test(text))continue;
    let parent=node.parentElement;
    for(let depth=0;parent&&depth<5;depth++,parent=parent.parentElement){
      const context=parent.innerText||'';
      if(context.length>800)break;
      if(/搜索历史|清空搜索历史/.test(context)){node.setAttribute('aria-label','搜索历史：'+text);break}
    }
  }
  // Some portals implement disabled confirmation with CSS rather than the
  // native disabled attribute. Expose that observed state to native snapshots.
  for(const doc of documents) for(const node of doc.querySelectorAll('button,a,span,div,[role=button]')){
    if(!/^(确定|确认)$/.test((node.innerText||'').replace(/\s/g,'')) || !node.getClientRects().length)continue;
    const disabled=node.hasAttribute('disabled') || /\b(?:dissure|disabled|is-disabled|ant-btn-disabled)\b/.test(node.className||'');
    if(disabled){node.setAttribute('aria-disabled','true');node.setAttribute('data-public-disabled','true')}
    else if(node.getAttribute('data-public-disabled')==='true'){node.removeAttribute('aria-disabled');node.removeAttribute('data-public-disabled')}
  }
  for(const doc of documents) for(const node of doc.querySelectorAll('input:not([type=password]):not([type=hidden]):not([readonly]):not([disabled])')){
    if(!/^(?:text|search|)$/.test((node.getAttribute('type')||'').toLowerCase()))continue;
    const identity=[node.id,node.name,node.className,node.getAttribute('placeholder')||'',node.getAttribute('aria-label')||''].join(' ');
    if(!node.getClientRects().length || /密码|账号|姓名|手机|身份证|验证码/.test(identity))continue;
    const container=node.closest('[class*=search],[id*=search],form');
    if(!/search|keyword|搜索|检索|关键词|事项/i.test(identity) && !container)continue;
    if(container && !/搜\s*索|检索/.test(container.innerText||'') && !/search|keyword/i.test(identity))continue;
    // Rotating example placeholders (e.g. Qinghai's "旅馆开办") otherwise
    // invalidate native getByRole(name=...) refs while the model is thinking.
    node.setAttribute('aria-label','公开事项搜索');
  }
  // Search results repeat identical guide buttons for unrelated services.
  // Give the existing native control its observed row title, so the model can
  // associate a ref with the right service without guessing button order.
  for(const doc of documents) for(const node of doc.querySelectorAll('button,a,[role=button]')){
    const action=(node.innerText||'').trim().replace(/\s/g,'');
    if(/^(确定|确认|搜索)$/.test(action)&&node.getClientRects().length)node.setAttribute('aria-label',node.disabled||node.getAttribute('aria-disabled')==='true'?action+'（当前不可点击）':action);
    if(!/^(办事指南|查看指南)$/.test((node.innerText||'').trim()) || !node.getClientRects().length) continue;
    // A wrapper link and its nested button can both enter the native tree.
    // Associate the service with the actual leaf control, not the wrapper.
    if(Array.from(node.querySelectorAll('button,a,[role=button]')).some(c=>/^(办事指南|查看指南)$/.test((c.innerText||'').trim())))continue;
    let parent=node.parentElement;
    for(let depth=0;parent&&depth<5;depth++,parent=parent.parentElement){
      const text=(parent.innerText||'').trim();
      if(text.length>1200)break;
      if(Array.from(parent.querySelectorAll('button,a,[role=button]')).filter(x=>/^(办事指南|查看指南)$/.test((x.innerText||'').trim())&&!Array.from(x.querySelectorAll('button,a,[role=button]')).some(c=>/^(办事指南|查看指南)$/.test((c.innerText||'').trim()))).length>1)break;
      const line=text.split('\n').map(x=>x.trim().replace(/(?:办事指南|查看指南|在线办理).*$/,'').trim()).find(x=>x.length<100 && /劳动.{0,35}(仲裁|调解).{0,15}(申请|申办|服务)/.test(x.replace(/\s/g,'')) && !/仲裁员|机构查询/.test(x));
      if(line){
        const child=text.split('\n').map(x=>x.trim()).find(x=>/^(案件进度查询|劳动者申请立案|用人单位申请立案)/.test(x));
        node.setAttribute('aria-label',(node.innerText||'').trim()+'：'+(child?child.replace(/个人|法人/g,'')+' · ':'')+line);break
      }
    }
  }
  for(const doc of documents) for(const node of doc.querySelectorAll('li,div,span,p,td')){
    const text=(node.innerText||'').trim();
    if(!text || text.length>100 || !node.getClientRects().length || node.hasAttribute('role')) continue;
    if(/在线办理|立即办理|登录|注册|验证码|预约|支付|仲裁员|资格审核|机构查询|委员会.*备案/.test(text)) continue;
    if(!/劳动.{0,35}(仲裁|调解).{0,15}(申请|指南|服务)|^(全省|站点切换|切换地区|请选择地区|查看指南|办事指南|申请材料|办理流程|表格下载|样例下载|下一页|确定|确认|搜索)$/.test(text.replace(/\s/g,''))) continue;
    if(!node.hasAttribute('onclick') && doc.defaultView.getComputedStyle(node).cursor!=='pointer') continue;
    const ancestor=node.parentElement?.closest('[role=button],button,a');
    if(ancestor && (ancestor.innerText||'').trim()===text)continue;
    node.setAttribute('role','button');node.setAttribute('aria-label',/^(确定|确认|搜索)$/.test(text.replace(/\s/g,''))?text.replace(/\s/g,''):text);
    marked.push({text,tag:node.tagName,url:doc.location.href});
    if(marked.length>=80)return marked;
  }
  return marked;
}
