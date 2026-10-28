"""Bindings for the retained Shanxi provincial portal application, SHA e07902e4.

Edit the official slots; retain punctuation, font, headings, signing and notes.
"""
import re
from docx import Document
from WenShu.template_fill import replace_span
from WenShu.exact_template_fill import value
from docx.oxml.ns import qn


def fill_application(data,path):
    doc=Document(path);paragraphs=doc.paragraphs
    if len(paragraphs)!=23 or '申请人（姓名）' not in paragraphs[3].text or paragraphs[6].text.strip()!='请求事项：' or paragraphs[10].text.strip()!='事实和理由' or '副本' not in paragraphs[12].text or '证据目录' not in paragraphs[13].text or '签名并捺印' not in paragraphs[16].text or '打印件需由申请人本人签名' not in paragraphs[18].text:
        raise ValueError('山西官方模板版本与已验证字段位置不一致，请重新核验')
    claims=[str(v).strip() for v in data.get('requests',[]) if str(v).strip()]
    if len(claims)>3:raise ValueError('山西当前模板最多支持3项请求')
    slots={
        3:[('申请人（姓名）：','，性别','applicantName'),('性别：','，出生日期','gender'),
           ('出生日期：','，民族','birthDate'),('民族：','，工作单位','nationality'),
           ('工作单位：','，现住址','applicantWorkUnit'),('现住址：','，联系电话','currentAddress'),
           ('联系电话：','。通讯地址','phone'),('通讯地址：','。','applicantMailingAddress')],
        4:[('被申请人（单位名称）：','。住所地','respondentName'),('住所地：','。','registeredAddress')],
        5:[('法定代表人或负责人：','。职务','legalRepName'),('职务：','。','legalRepPosition'),
           ('联系电话：','。','legalRepPhone')],
    }
    for index,bindings in slots.items():
        paragraph=paragraphs[index];changes=[]
        for label,ending,key in bindings:
            content=value(data,key)
            if not content:continue
            match=re.search(re.escape(label)+r'(?P<slot>.*?)(?='+re.escape(ending)+')',paragraph.text)
            if not match:raise ValueError('山西模板字段缺失：'+label)
            changes.append((match.start('slot'),match.end('slot'),content))
        for start,end,content in sorted(changes,reverse=True):replace_span(paragraph,start,end,content)
    if claims:
        for index in range(3):
            if index<len(claims):replace_span(paragraphs[7+index],2,len(paragraphs[7+index].text),claims[index])
            else:paragraphs[7+index]._p.getparent().remove(paragraphs[7+index]._p)
    if data.get('factsReason'):replace_span(paragraphs[11],0,len(paragraphs[11].text),str(data['factsReason']).strip())
    if data.get('copyCount') is not None:
        match=re.search(r'副本(?P<slot>\s+)(?=份)',paragraphs[12].text)
        if not match:raise ValueError('山西模板副本份数字段缺失')
        replace_span(paragraphs[12],match.start('slot'),match.end('slot'),str(data['copyCount']))
    if value(data,'committeeName'):replace_span(paragraphs[15],0,len(paragraphs[15].text),value(data,'committeeName'))
    if value(data,'applicationDate'):replace_span(paragraphs[17],0,len(paragraphs[17].text),value(data,'applicationDate'))
    # Human signature is left blank. Keep signature, date and the first note together.
    if claims or data.get('factsReason'):
        for paragraph in paragraphs[14:18]:paragraph.paragraph_format.keep_with_next=True
    # The acquired original ends with an empty next-page section, whose page
    # geometry is identical. Remove only that empty tail in generated copies.
    if len(paragraphs)==23 and all(not p.text.strip() for p in paragraphs[21:]):
        section=paragraphs[21]._p.find('./'+qn('w:pPr')+'/'+qn('w:sectPr'))
        final=doc._element.body.find(qn('w:sectPr'))
        if section is not None and final is not None and section.xml==final.xml:
            for paragraph in paragraphs[21:]:paragraph._p.getparent().remove(paragraph._p)
    return doc
