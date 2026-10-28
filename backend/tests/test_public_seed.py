"""Fresh clones load public data once, existing and private databases stay intact."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest
from regional_directory import DirectoryStore

class PublicSeedTests(unittest.TestCase):
    def module(self):
        import public_seed
        return public_seed

    def bundle(self,root):
        seed=root/'data/public-regions';seed.mkdir(parents=True)
        guide={'province':'sichuan','city':'成都市','district':'测试区','region_code':'510199000000',
            'service_name':'劳动人事争议仲裁申请','source_url':'https://www.sczwfw.gov.cn/guide?areaCode=510199000000',
            'source_id':digest('https://www.sczwfw.gov.cn/guide?areaCode=510199000000')[:24],
            'verification_status':'verified','collected_at':'2026-10-28T00:00:00Z','verified_at':'2026-10-28T00:00:00Z',
            'templates':[{'id':'own','region_code':'510199000000','file':'templates/_docx/_regional/510199000000/missing.docx',
                'download_status':'downloaded','sha256':'0'*64,'can_generate':True,'adapter':'unverified','document_types':['application']}],
            'fields':{},'sections':{},'materials':[],'warnings':[]}
        area={'provider':'official_test','code':'510199000000','province':'sichuan','city':'成都市','district':'测试区',
            'level':4,'source_url':guide['source_url'],'collected_at':guide['collected_at']}
        files={}
        for name,body in [('guides.json',[guide]),('directory.json',[area])]:
            p=seed/name;p.write_text(json.dumps(body,ensure_ascii=False),encoding='utf8');files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
        (seed/'manifest.json').write_text(json.dumps({'schema_version':1,'files':files}),encoding='utf8')
        return seed,guide

    def test_empty_public_databases_load_once_and_missing_attachment_never_generates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.bundle(root);result=self.module().bootstrap_public_data(root)
            self.assertEqual((result['guides_imported'],result['directory_imported']),(1,1))
            own=RegionalStore(root/'backend/data/regional-guides.sqlite').lookup('sichuan','成都市','测试区')
            self.assertFalse(own['templates'][0]['can_generate'])
            self.assertEqual(self.module().bootstrap_public_data(root)['guides_imported'],0)
            self.assertFalse((root/'backend/data/labourlawyer.db').exists())

    def test_existing_public_data_is_not_merged_or_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,guide=self.bundle(root)
            store=RegionalStore(root/'backend/data/regional-guides.sqlite');guide['district']='已有地区';store.put_guide(guide)
            directory=DirectoryStore(root/'backend/data/regional-directory.sqlite');directory.put_area({'provider':'own','code':'old',
                'province':'sichuan','city':'已有市','district':'已有区','level':4,'source_url':'https://www.sczwfw.gov.cn/', 'collected_at':'2026-10-28'})
            before=(store.path.read_bytes(),directory.path.read_bytes())
            result=self.module().bootstrap_public_data(root)
            self.assertEqual((result['guides_imported'],result['directory_imported']),(0,0))
            self.assertEqual((store.path.read_bytes(),directory.path.read_bytes()),before)

    def test_changed_snapshot_fails_before_any_database_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);seed,_=self.bundle(root);(seed/'guides.json').write_text('[]',encoding='utf8')
            with self.assertRaises(ValueError):self.module().bootstrap_public_data(root)
            self.assertFalse((root/'backend/data').exists())

if __name__=='__main__':unittest.main()
