import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const {createRouter,createMemoryHistory}=require('vue-router')
const provinces=JSON.parse(readFileSync(new URL('../frontend/src/data/provinceCatalog.json',import.meta.url),'utf8'))
const text=readFileSync(new URL('../frontend/src/router/index.js',import.meta.url),'utf8')
const body=text.replace(/^import .*$/gm,'').replace(/const (\w+) = \(\) => import\([^\n]+/g,'const $1 = {}').replace('import.meta.env.BASE_URL',"'/'").replace('export default router','return router')
globalThis.document={title:''}
const router=new Function('createRouter','createWebHistory','findProvince','PublicHome',body)(createRouter,createMemoryHistory,slug=>provinces.find(p=>p.slug===slug),{})
const cases=[
 ['/documents/jiangsu/application?city=苏州市&district=相城区','/local-documents/jiangsu/application'],
 ['/documents/jiangsu/evidence?city=苏州市&district=吴江区&source_id=own-source&version=3#confirm','/local-documents/jiangsu/evidence'],
 ['/documents/anhui/application?city=合肥市&district=肥东县','/local-documents/anhui/application'],
 ['/documents/jiangsu/application','/documents/jiangsu/application'],
 ['/documents/zhejiang/evidence','/documents/zhejiang/evidence'],
 ['/documents/jiangsu/application?city=苏州市','/province/jiangsu'],
 ['/documents/jiangsu/application?district=相城区','/province/jiangsu'],
 ['/documents/jiangsu/application?city=苏州市&city=无锡市&district=相城区','/province/jiangsu'],
 ['/documents/jiangsu/application?city=&district=相城区','/province/jiangsu'],
 ['/documents/not-a-province/application?city=苏州市&district=相城区','/'],
 ['/local-documents/jiangsu/application?city=苏州市&district=相城区','/local-documents/jiangsu/application'],
]
for(const [url,expected] of cases){
 await router.push(url)
 const actual=router.currentRoute.value
 assert.equal(actual.path,expected,url)
 if(expected.startsWith('/local-documents/')||expected==='/province/jiangsu'){
  const resolved=router.resolve(url)
  assert.deepEqual(actual.query,resolved.query,'Scope queries must survive: '+url)
  assert.equal(actual.hash,resolved.hash,'Hash must survive: '+url)
 }
}
console.log(`PASS regional document routing: ${cases.length} real memory-router guard cases`)
