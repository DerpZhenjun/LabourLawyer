"""Bounded read-only inspection of preserved newer-portal evidence."""
import json
from pathlib import Path
from lxml import html

BASE=Path(__file__).resolve().parents[1]/'reports/nationwide-localization-20261023-night/sichuan/v4/captures'
for path in sorted(BASE.glob('*/manifest.json')):
    manifest=json.loads(path.read_text('utf8'))
    folder=path.parent
    snapshots=[json.loads((folder/s['file']).read_text('utf8')) for s in manifest['sections']]
    dom=html.fromstring(snapshots[1]['html'])
    print(manifest['region_code'],manifest['city'],manifest['district'],len(snapshots))
    if manifest['region_code']!='510704000000':
        print(' material:',snapshots[1]['text'].split('常见问题')[-1].split('网站信息')[0][:220])
        continue
    node=dom.get_element_by_id('material')
    print(' ancestors:',[(n.tag,n.get('id'),n.get('class'),n.get('style')) for n in node.iterancestors()])
    print(' siblings:',[(n.tag,n.get('id'),n.get('class'),n.get('style'),n.text_content().strip()[:100]) for n in node.getparent()])
    for link in dom.xpath('//a[@onclick]'):
        if 'download' in link.get('onclick','') or 'biao' in link.get('onclick',''):
            print(' link:',link.text_content().strip()[:70],link.get('onclick'),[(a.tag,a.get('class')) for a in list(link.iterancestors())[:7]])
    print(' selected panel:')
    for index,snap in enumerate(snapshots):
        tree=html.fromstring(snap['html'])
        panels=tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," content3_text ") and contains(concat(" ",normalize-space(@class)," ")," on ")]')
        tabs=tree.xpath('//ul[contains(@class,"content3_title_list")]/li')
        print(index,[(n.get('class'),n.text_content().strip()[:65]) for n in panels],[(n.get('class'),n.text_content().strip()) for n in tabs[:8]])
    for script in dom.xpath('//script[not(@src)]'):
        text=script.text_content()
        for name in ['downloadAnnexFile','biao1','biao2']:
            pos=text.find('function '+name)
            if pos>=0:print(' function:',text[pos:pos+1000])
