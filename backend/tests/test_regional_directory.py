import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from regional_directory import DirectoryStore, national_children


class RegionalDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = DirectoryStore(Path(self.temp.name) / 'directory.sqlite')

    def test_rejects_wrong_parent_in_official_response(self):
        response = {'success': True, 'code':200, 'data':[
            {'regionCode':'510106','regionName':'金牛区','parentId':'510100','regionLvl':'4'}]}
        with self.assertRaises(ValueError):
            national_children(response, '370100')

    def test_directory_does_not_grant_generation_or_cross_city_data(self):
        self.store.put_area({'provider':'national','code':'110105','province':'beijing','city':'北京市','district':'朝阳区','level':4,'parent_code':'110100','source_url':'https://gjzwfw.www.gov.cn/fwmh/ucGovRegion/findUcGovRegion.do','collected_at':'2026-10-23T14:00:00Z'})
        self.store.put_area({'provider':'national','code':'220104','province':'jilin','city':'长春市','district':'朝阳区','level':4,'parent_code':'220100','source_url':'https://gjzwfw.www.gov.cn/fwmh/ucGovRegion/findUcGovRegion.do','collected_at':'2026-10-23T14:00:00Z'})
        result = self.store.areas('jilin','长春市')
        self.assertEqual([r['code'] for r in result], ['220104'])
        self.assertFalse(result[0]['can_generate'])
        self.assertIsNone(result[0]['source_id'])

    def test_provider_qualified_codes_keep_functional_area_separate(self):
        common = {'code':'510109','province':'sichuan','city':'成都市','level':4,'parent_code':'510100','source_url':'https://www.sczwfw.gov.cn/','collected_at':'2026-10-23T14:00:00Z'}
        self.store.put_area({**common,'provider':'national','district':'某行政区'})
        self.store.put_area({**common,'provider':'sichuan_portal','district':'成都高新区'})
        self.assertEqual(len(self.store.areas('sichuan','成都市')), 2)

    def test_failed_directory_response_cannot_erase_previous_records(self):
        self.store.put_area({'provider':'national','code':'510106','province':'sichuan','city':'成都市','district':'金牛区','level':4,'parent_code':'510100','source_url':'https://gjzwfw.www.gov.cn/','collected_at':'2026-10-23T14:00:00Z'})
        with self.assertRaises(ValueError):
            national_children({'success':False,'data':None,'message':'返回结果为null'},'510100')
        self.assertEqual(self.store.areas('sichuan','成都市')[0]['district'],'金牛区')

    def test_queue_resumes_interrupted_job_without_duplicate_enqueue(self):
        key = self.store.enqueue('directory', {'provider':'national','parent':'510000'})
        self.assertEqual(self.store.enqueue('directory', {'provider':'national','parent':'510000'}),key)
        job = self.store.claim()
        self.assertEqual(job['id'], key)
        self.assertIsNone(self.store.claim())
        self.store.recover_interrupted()
        self.assertEqual(self.store.claim()['id'],key)
        self.store.finish(key, 'done', {'count':21})
        self.assertIsNone(self.store.claim())

    def test_recovering_one_worker_does_not_steal_another_workers_running_job(self):
        first=self.store.enqueue('directory',{'parent':'110000'})
        second=self.store.enqueue('sichuan_capture',{'region_code':'510302000000'})
        self.store.claim('directory');self.store.claim('sichuan_capture')
        self.store.recover_interrupted('directory')
        self.assertEqual(self.store.claim('directory')['id'],first)
        self.assertIsNone(self.store.claim('sichuan_capture'))
        self.store.finish(second,'needs_browser',{})

    def test_summary_does_not_count_same_place_twice_from_two_providers(self):
        common={'code':'510106','province':'sichuan','city':'成都市','district':'金牛区','level':4,'parent_code':'510100','source_url':'https://www.sczwfw.gov.cn/','collected_at':'2026-10-23T14:00:00Z'}
        self.store.put_area({**common,'provider':'national'})
        self.store.put_area({**common,'provider':'sichuan_portal'})
        self.assertEqual(self.store.summary()['areas'],[{'province':'sichuan','level':4,'count':1}])

    def test_direct_county_terminal_remains_selectable_without_fake_child_query(self):
        from regional_directory import national_area
        row={'regionCode':'469005','regionName':'文昌市','parentId':'460000','regionLvl':'3'}
        result=national_area(row,'hainan','',{'url':'https://gjzwfw.www.gov.cn/','collected_at':'2026-10-23T14:00:00Z','sha256':'fixture'})
        self.assertEqual(result['level'],4)
        self.assertTrue(result['directory_terminal'])
        self.assertEqual(result['raw_record']['regionLvl'],'3')
        self.store.put_area(result)
        self.assertEqual(self.store.areas('hainan')[0]['city'],'文昌市')
        self.assertEqual(self.store.areas('hainan','文昌市')[0]['district'],'文昌市')

    def test_province_direct_level_four_county_keeps_complete_selection_path(self):
        from regional_directory import national_area
        row={'regionCode':'130181','regionName':'辛集市','parentId':'130000','regionLvl':'4'}
        result=national_area(row,'hebei','',{'url':'https://gjzwfw.www.gov.cn/','collected_at':'2026-10-23T14:00:00Z','sha256':'fixture'})
        self.store.put_area(result)
        self.assertEqual(self.store.areas('hebei')[0]['city'],'辛集市')
        self.assertEqual(self.store.areas('hebei','辛集市')[0]['district'],'辛集市')

    def test_municipality_terminal_district_does_not_become_a_fake_city(self):
        from regional_directory import national_area
        row={'regionCode':'500101','regionName':'万州区','parentId':'500000','regionLvl':'3'}
        result=national_area(row,'chongqing','重庆市',{'url':'https://gjzwfw.www.gov.cn/','collected_at':'2026-10-23T14:00:00Z','sha256':'fixture'})
        self.store.put_area(result)
        self.assertEqual(self.store.areas('chongqing')[0]['city'],'重庆市')
        self.assertEqual(self.store.areas('chongqing','重庆市')[0]['district'],'万州区')

    def test_inactive_or_malformed_records_are_not_publishable(self):
        response = {'success':True,'code':200,'data':[
            {'regionCode':'510106','regionName':'金牛区','parentId':'510100','regionLvl':'4','del_flag':1},
            {'regionCode':'510107','regionName':'武侯区','parentId':'510100','regionLvl':'4','del_flag':0,'regionStatus':'US01'}]}
        self.assertEqual([r['regionCode'] for r in national_children(response,'510100')],['510107'])
        with self.assertRaises(ValueError):
            national_children({'success':True,'code':200,'data':[{'regionCode':'../../a','regionName':'错误','parentId':'510100','regionLvl':'4'}]},'510100')


class DirectoryAPITests(unittest.TestCase):
    def test_city_filter_does_not_inherit_province_generation(self):
        import os
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.regional_guides import router
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{
            'LABOURLAWYER_DIRECTORY_DB':str(Path(folder)/'directory.sqlite'),
            'LABOURLAWYER_REGIONAL_DB':str(Path(folder)/'guides.sqlite')}):
            directory = DirectoryStore(Path(folder)/'directory.sqlite')
            directory.put_area({'provider':'national','code':'370171','province':'shandong','city':'济南市','district':'济南高新区','level':4,'parent_code':'370100','source_url':'https://gjzwfw.www.gov.cn/','collected_at':'2026-10-23T14:00:00Z'})
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            client=TestClient(app)
            response=client.get('/api/regional-guides/areas',params={'province':'shandong','city':'济南市'})
            self.assertEqual(response.status_code,200)
            result=response.json()
            self.assertEqual([r['district'] for r in result['items']],['济南高新区'])
            self.assertIsNone(result['items'][0]['source_id'])
            self.assertFalse(result['items'][0]['can_generate'])
            self.assertEqual(client.get('/api/regional-guides/areas',params={'province':'shandong','city':'青岛市'}).json()['items'],[])
