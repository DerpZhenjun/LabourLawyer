import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from regional_anhui_oct29 import load_guide, fill_feidong_application

BASE=Path(__file__).resolve().parent
def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

for locality in ('yaohai','feidong'):
    save(BASE/locality/'guide.json',load_guide(locality))

payloads={
    'fictional-short':{
        'applicant_lines':['张虚构，女，三十岁，示例公司职员','肥东县示例路一号；电话00000000'],
        'agent_lines':['王虚构，虚构委托代理人','肥东县示例街三号；电话00000001'],
        'respondent_lines':['肥东县虚构示例有限公司','肥东县示例路二号；电话00000002'],
        'representative_lines':['李虚构，总经理','联系电话00000003'],
        'requests':['一、请求支付虚构工资一万元。','二、请求支付虚构经济补偿二千元。'],
        'facts':'本文件全部为离线验收虚构资料。申请人曾在被申请人处从事示例工作。双方在虚构日期解除劳动关系，尚有工资未支付。证据为虚构劳动合同及工资记录。证人王虚构，住所为肥东县示例街四号。'
    },
    'fictional-capacity':{
        'applicant_lines':['虚构甲'*6+'甲乙','虚构乙'*8+'乙'],
        'agent_lines':['虚构丙'*6+'丙丁','虚构丁'*8+'丁'],
        'respondent_lines':['虚构戊'*6+'戊己','虚构己'*8+'己'],
        'representative_lines':['虚构庚'*6+'庚辛','虚构辛'*8+'辛'],
        'requests':['虚构请求'*59+'虚构甲乙丙丁戊己庚辛'],
        'facts':'虚构事实'*70
    }
}
tasks=[]
for name,payload in payloads.items():
    target=BASE/'feidong/qa'/(name+'-final')
    target.mkdir(exist_ok=True)
    save(target/'payload.json',payload)
    path=target/'filled.docx'
    path.write_bytes(fill_feidong_application(load_guide('feidong'),payload))
    tasks.append({'source':str(path),'pdf':str(target/'filled.pdf')})
save(BASE/'qa/final-filled-tasks.json',tasks)
