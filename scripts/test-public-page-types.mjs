import assert from 'node:assert/strict'
import {existsSync,readFileSync,mkdirSync,writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {createRequire} from 'node:module'
import {spawnSync} from 'node:child_process'
const root=fileURLToPath(new URL('../',import.meta.url)),require=createRequire(new URL('../frontend/package.json',import.meta.url))
const owned=['views/PublicHome','views/ProvinceGuide','views/RegionalGuide','views/RegionalDocument','views/RegionalCollection','views/Home','components/ProvinceCard','components/PublicHeader','components/BrandMark','components/ServiceIllustration','components/RegionalRollout','components/RegionalVerification']
for(const name of ['data/provinces','data/regionalGuidePresentation','composables/useRegionDirectory'])assert(existsSync(new URL(`../frontend/src/${name}.ts`,import.meta.url)),`True typed module required: ${name}`)
const ts=require('typescript'),compiler=require('@vue/compiler-sfc')
const vue=require('vue'),presentation=await import(new URL('../frontend/src/data/regionalGuidePresentation.ts',import.meta.url)),provinceData=await import(new URL('../frontend/src/data/provinces.ts',import.meta.url))
const tick=async()=>{await Promise.resolve();await vue.nextTick();await new Promise(setImmediate);await vue.nextTick()}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});return{promise,resolve,reject}}
globalThis.Document=class {};globalThis.ShadowRoot=class {}
const node=(type,text='')=>({type,text,children:[],props:{},parent:null,events:{},addEventListener(key,fn){this.events[key]=fn},getRootNode(){return{}}})
const insert=(el,parent,anchor)=>{if(el.parent){const i=el.parent.children.indexOf(el);if(i>=0)el.parent.children.splice(i,1)}el.parent=parent;const i=anchor?parent.children.indexOf(anchor):-1;if(i<0)parent.children.push(el);else parent.children.splice(i,0,el)}
const renderer=vue.createRenderer({createElement:node,createText:t=>node('#text',t),createComment:t=>node('#comment',t),setText:(n,t)=>{n.text=t},setElementText:(n,t)=>{n.text=t;n.children=[]},patchProp:(n,k,old,v)=>{n.props[k]=v},insert,remove:n=>{if(n.parent)n.parent.children.splice(n.parent.children.indexOf(n),1)},parentNode:n=>n.parent,nextSibling:n=>n.parent?.children[n.parent.children.indexOf(n)+1]??null,setScopeId:()=>{},insertStaticContent:(html,p,a)=>{const n=node('#static',html);insert(n,p,a);return[n,n]}})
const all=n=>[n,...n.children.flatMap(all)],content=n=>n.text+n.children.map(content).join('')
function evaluate(code,modules){
 code=code.replaceAll('import.meta.env.BASE_URL',JSON.stringify('/preview/'))
 code=ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText
 code=code.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];?/g,(_,names,from)=>`const {${names.replace(/\s+as\s+/g,':')}}=__modules[${JSON.stringify(from)}];`).replace(/import\s+([\w$]+)\s+from\s*['"]([^'"]+)['"];?/g,(_,name,from)=>`const ${name}=__modules[${JSON.stringify(from)}];`).replace(/import\s*['"][^'"]+['"];?/g,'').replace('export default','return')
 return new Function('__modules',code)({vue,...modules})
}
const compile=(name,modules)=>{const filename=root+'frontend/src/'+name+'.vue',descriptor=compiler.parse(readFileSync(filename,'utf8'),{filename}).descriptor;return evaluate(compiler.compileScript(descriptor,{id:name,inlineTemplate:true}).content,modules)}
const link=vue.defineComponent({setup:(p,{slots})=>()=>vue.h('a',{},slots.default?.())})
const brand=compile('components/BrandMark',{}),brandHost=node('root'),brandApp=renderer.createApp(brand,{variant:'assistant',size:40,label:'咨询图标'});brandApp.mount(brandHost)
const image=all(brandHost).find(n=>n.type==='img');assert.equal(image.props.src,'/preview/brand/counsel-mark.svg');assert.equal(image.props.alt,'咨询图标');assert.equal(image.props.width,40);brandApp.unmount()
const headerRoute=vue.reactive({fullPath:'/',path:'/',hash:''}),Header=compile('components/PublicHeader',{'vue-router':{RouterLink:link,useRoute:()=>headerRoute},'./BrandMark.vue':brand}),headerHost=node('root'),headerApp=renderer.createApp(Header);headerApp.mount(headerHost)
const menu=all(headerHost).find(n=>n.type==='button');assert.equal(menu.props['aria-expanded'],false);menu.props.onClick();await tick();assert.equal(menu.props['aria-expanded'],true);headerRoute.fullPath='/province/fixture';await tick();assert.equal(menu.props['aria-expanded'],false);assert(all(headerHost).some(n=>n.type==='a'&&n.props.href==='#main-content'));headerApp.unmount()
console.log('PASS mounted brand keeps native base URLs and header menu closes on navigation with skip link intact')
assert.equal(provinceData.provinces.length,JSON.parse(readFileSync(new URL('../frontend/src/data/provinceCatalog.json',import.meta.url),'utf8')).length)
for(const p of provinceData.provinces){assert.equal(provinceData.findProvince(p.slug),p);assert.equal(typeof provinceData.documentFormLimits(p.slug).maxRequests,'number');assert.equal(typeof provinceData.makeApplicationExample(p).factsReason,'string');assert(provinceData.makeEvidenceExample(p).evidenceList.every(e=>typeof e.pageRange==='string'))}
const formConfig=JSON.parse(readFileSync(new URL('../config/document_forms.json',import.meta.url),'utf8'))
for(const key of ['applicationExtraFields','evidenceExtraFields','applicationSupportedFields','evidenceSupportedFields'])assert.deepEqual(provinceData[key],formConfig[key])
assert.equal(provinceData.findProvince('not-a-province'),undefined)
const snapshot=JSON.parse(readFileSync(new URL('../frontend/src/data/provinceExperiences.json',import.meta.url),'utf8'))
for(const [slug,raw]of Object.entries(snapshot.provinces))assert.equal(presentation.readExperience(raw,slug).slug,slug)
const provinceRoute=vue.reactive({params:{slug:'zhejiang'}}),experiences=[],experienceQueue=[]
const ProvinceGuide=compile('views/ProvinceGuide',{'vue-router':{RouterLink:link,useRoute:()=>provinceRoute},'@/api/public':{publicClient:{experience:(slug,signal)=>{const pending=deferred();experiences.push({slug,signal});experienceQueue.push(pending);return pending.promise}}},'@/data/regionalGuidePresentation':presentation,'@/components/DistrictWorkflow.vue':vue.defineComponent({setup:()=>()=>vue.h('aside')}),'@/data/provinces':provinceData,'@/data/provinceExperiences.json':snapshot,'../../../config/province_themes.json':JSON.parse(readFileSync(new URL('../config/province_themes.json',import.meta.url),'utf8'))})
const provinceHost=node('root'),provinceApp=renderer.createApp(ProvinceGuide);provinceApp.mount(provinceHost);await tick();provinceRoute.params.slug='jiangsu';await tick();assert(experiences[0].signal.aborted)
experienceQueue[1].resolve({...presentation.readExperience(snapshot.provinces.jiangsu,'jiangsu'),scope:'虚构江苏新记录'});await tick();experienceQueue[0].resolve({...presentation.readExperience(snapshot.provinces.zhejiang,'zhejiang'),scope:'虚构浙江旧记录'});await tick();assert.match(content(provinceHost),/虚构江苏新记录/);assert.doesNotMatch(content(provinceHost),/虚构浙江旧记录/);provinceApp.unmount();assert(experiences[1].signal.aborted)
console.log('PASS mounted province guide keeps its historical snapshot and rejects a late previous province experience')
const guides=JSON.parse(readFileSync(new URL('../data/public-regions/guides.json',import.meta.url),'utf8'))
const {assertRegionalGuide}=await import(new URL('../packages/regional-contracts/src/index.ts',import.meta.url))
for(const raw of guides){
  // The immutable seed has no database sequence. Exercise the real wire parser
  // with a test-only live version before checking its rendered projection.
  const live=assertRegionalGuide({...raw,version:1},raw)
  assert.equal(presentation.readGuideDisplay(live).source_id,raw.source_id)
}
const capturedGuide=guides.find(g=>g.region_code==='320507');assert(capturedGuide)
// Snapshot files have no live-store sequence; this is a local test-only version.
const ownGuide={...capturedGuide,version:1}
const guideRef=vue.ref(ownGuide),templateCalls=[],guideRoute=vue.reactive({params:{slug:ownGuide.province},query:{city:ownGuide.city,district:ownGuide.district}})
const Guide=compile('views/RegionalGuide',{'@/data/regionalGuidePresentation':presentation,'vue-router':{RouterLink:link,useRoute:()=>guideRoute,useRouter:()=>({replace:()=>{}})},'@/data/provinces':provinceData,'@/api/public':{publicClient:{inventory:async()=>({items:[],coverage:[]})}},'@/composables/useRegionalGuide':{useRegionalGuide:()=>({guide:guideRef,loading:vue.ref(false),error:vue.ref(''),reload:()=>{}}),templateURL:(region,id,binding)=>{templateCalls.push({region,id,binding});return'/fixture-original/'+id}},'@/components/DocumentWorkspace.vue':vue.defineComponent({setup:()=>()=>vue.h('section')}),'@/composables/useRegionDirectory':{useRegionDirectory:()=>({cityAreas:vue.ref([]),districtAreas:vue.ref([]),directoryLoading:vue.ref(false),directoryError:vue.ref('')})}})
const guideHost=node('root'),guideApp=renderer.createApp(Guide);guideApp.mount(guideHost);await tick();assert(templateCalls.length>0);for(const call of templateCalls)assert.deepEqual(call.binding,{source_id:ownGuide.source_id,version:ownGuide.version})
templateCalls.length=0;guideRef.value={...ownGuide,source_id:null};await tick();assert.equal(templateCalls.length,0);guideApp.unmount()
console.log('PASS mounted local guide binds original downloads to its exact source/version and exposes no original for unverified scope')
assert.throws(()=>presentation.readExperience({slug:'foreign',steps:[]},'own'))
assert.throws(()=>presentation.readAreaRows([{province:'foreign',city:'虚构市'}],'own'))
assert.throws(()=>presentation.readRollout({provinces:[],directory_is_not_guide_coverage:true,published_guides:'202'}))
assert.throws(()=>presentation.readCollectionReport({openclaw:{status:'pending',pending_count:'x'},categories:{},regions:[]}))
console.log('PASS typed presentation decodes all retained local guides and province experiences; malformed/foreign JSON rejects')
const route=vue.reactive({path:'/',fullPath:'/',query:{q:''},hash:''}),calls=[]
const Home=compile('views/PublicHome',{'vue-router':{useRoute:()=>route,useRouter:()=>({replace:r=>{calls.push(r);route.query=r.query}})},'@/data/provinces':provinceData,'@/components/ServiceIllustration.vue':vue.defineComponent({setup:()=>()=>vue.h('figure')}),'@/components/ProvinceCard.vue':vue.defineComponent({props:['province'],setup:p=>()=>vue.h('article',{'data-province':p.province.slug})})})
const homeHost=node('root'),homeApp=renderer.createApp(Home);homeApp.mount(homeHost);await tick()
assert.equal(all(homeHost).filter(n=>n.props['data-province']).length,6)
const search=all(homeHost).find(n=>n.type==='input');search.props['onUpdate:modelValue']('浙江');await tick();assert.equal(all(homeHost).filter(n=>n.props['data-province']).length,1);assert.equal(calls.at(-1).query.q,'浙江')
search.props['onUpdate:modelValue']('不存在的虚构省');await tick();assert.match(content(homeHost),/没有找到这个省份/);homeApp.unmount()
console.log('PASS mounted public home keeps six featured provinces and route-linked search/empty state')
const old=deferred(),fresh=deferred(),queue=[old,fresh],rolloutFetch=globalThis.fetch
globalThis.fetch=async()=>Response.json(await queue.shift().promise)
const status=name=>({directory_is_not_guide_coverage:true,published_guides:1,generatable_localities:1,unpublished_candidates:0,targets_total:1,provinces:[{slug:'fixture',name,targets_total:1,published_guides:1,generatable_localities:1,candidates:0,uncollected:0}]})
const Rollout=compile('components/RegionalRollout',{'vue-router':{RouterLink:link},'@/composables/useRegionalGuide':{regionalAPI:'https://fixture.invalid/api'},'@/api/public':{publicClient:{rollout:async()=>await queue.shift().promise}},'@/data/regionalGuidePresentation':presentation})
const rolloutHost=node('root'),rolloutApp=renderer.createApp(Rollout),rollout=rolloutApp.mount(rolloutHost);const refresh=rollout.refresh();fresh.resolve(status('虚构新区'));await refresh;await tick();old.resolve(status('虚构旧区'));await tick();assert.match(content(rolloutHost),/虚构新区/);assert.doesNotMatch(content(rolloutHost),/虚构旧区/);rolloutApp.unmount();globalThis.fetch=rolloutFetch
console.log('PASS mounted rollout rejects an aborted late response after refresh')
const directorySource=readFileSync(new URL('../frontend/src/composables/useRegionDirectory.ts',import.meta.url),'utf8')
const areaCalls=[],areaQueue=[],mockDirectory={areas:(province,city,signal)=>{const pending=deferred();areaCalls.push({province,city,signal});areaQueue.push(pending);return pending.promise}}
const directory=evaluate(directorySource.replace('export function useRegionDirectory','function useRegionDirectory')+'\nreturn {useRegionDirectory}',{'../api/public.ts':{publicClient:mockDirectory},'../data/regionalGuidePresentation.ts':presentation})
const selection=vue.ref({province:'fixture-a',city:'虚构甲市',district:''});let state
const dirApp=renderer.createApp({setup(){state=directory.useRegionDirectory(selection);return()=>vue.h('div')}});dirApp.mount(node('root'));await new Promise(r=>setTimeout(r,205));assert.equal(areaCalls.length,2)
selection.value={province:'fixture-b',city:'虚构乙市',district:''};assert.equal(areaCalls[0].signal.aborted,true);assert.deepEqual(state.cityAreas.value,[]);assert.deepEqual(state.districtAreas.value,[]);await new Promise(r=>setTimeout(r,205));assert.equal(areaCalls.length,4)
const area=(province,city,district)=>({province,city,district,region_code:'990001',can_generate:false,source_id:null})
areaQueue[2].resolve([area('fixture-b','虚构乙市','')]);areaQueue[3].resolve([area('fixture-b','虚构乙市','虚构乙区')]);await tick();areaQueue[0].resolve([area('fixture-a','虚构甲市','')]);areaQueue[1].resolve([area('fixture-a','虚构甲市','虚构甲区')]);await tick();assert.equal(state.districtAreas.value[0].district,'虚构乙区');dirApp.unmount();assert.equal(areaCalls[3].signal.aborted,true)
console.log('PASS mounted directory clears scope immediately, aborts pending requests and ignores late foreign areas')
const clientSource=readFileSync(new URL('../frontend/src/api/public.ts',import.meta.url),'utf8'),httpCalls=[];let httpResult
const publicAPI=evaluate(clientSource.replace('export const publicClient=','const publicClient=')+'\nreturn {publicClient}',{'./http.ts':{readJSON:async(path,options)=>{httpCalls.push({path,options});return httpResult}},'../../../packages/regional-contracts/src/index.ts':await import(new URL('../packages/regional-contracts/src/index.ts',import.meta.url)),'../data/regionalGuidePresentation.ts':presentation}).publicClient
const abort=new AbortController();httpResult={items:[area('fixture-b','虚构乙市','虚构乙区')]};assert.equal((await publicAPI.areas('fixture-b','虚构乙市',abort.signal))[0].district,'虚构乙区');assert.equal(httpCalls.at(-1).options.signal,abort.signal);assert.match(httpCalls.at(-1).path,/^\/api\/regional-guides\/areas\?province=fixture-b&city=/)
httpResult={openclaw:{status:'PENDING',pending_count:0,attempted_at:null,total_count:0,acknowledged_count:0,exported_count:0,ai_reviewed_count:0},regions:[],categories:{},extra_public_field:{preserved:true}};const report=await publicAPI.report();assert.equal(report.raw,httpResult);assert.equal(report.raw.extra_public_field.preserved,true)
httpResult={...httpResult,openclaw:{status:'PENDING',pending_count:0,attempted_at:null}};await assert.rejects(()=>publicAPI.report())
httpResult={slug:'foreign',steps:[]};await assert.rejects(()=>publicAPI.experience('own'))
console.log('PASS unified public client binds directory/experience scope, forwards cancellation and preserves complete raw report export')
for(const name of owned){
 const source=readFileSync(new URL(`../frontend/src/${name}.vue`,import.meta.url),'utf8'),parsed=compiler.parse(source).descriptor
 assert.equal(parsed.scriptSetup?.lang,'ts',`Actual typed script required: ${name}`)
 const ast=ts.createSourceFile(name,parsed.scriptSetup.content,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS)
 const visit=n=>{assert.notEqual(n.kind,ts.SyntaxKind.AnyKeyword,`No any annotation: ${name}`);ts.forEachChild(n,visit)};visit(ast)
 assert(!/@ts-(?:ignore|nocheck)/.test(source),`No suppressed checks: ${name}`)
}
for(const relative of ['data/provinces.ts','data/regionalGuidePresentation.ts','composables/useRegionDirectory.ts','api/public.ts']){
 const source=readFileSync(new URL('../frontend/src/'+relative,import.meta.url),'utf8'),ast=ts.createSourceFile(relative,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS)
 const visit=n=>{assert.notEqual(n.kind,ts.SyntaxKind.AnyKeyword,`No any annotation: ${relative}`);ts.forEachChild(n,visit)};visit(ast)
 assert(!/@ts-(?:ignore|nocheck)/.test(source))
}
const scratch=new URL('../.runtime/public-page-types/',import.meta.url);mkdirSync(scratch,{recursive:true})
const negative=`import {ref} from '../../frontend/node_modules/vue'
import type {ProvinceDefinition,FormLimits,DocumentFieldDefinition} from '../../frontend/src/data/provinces.ts'
import {useRegionDirectory} from '../../frontend/src/composables/useRegionDirectory.ts'
import {publicClient} from '../../frontend/src/api/public.ts'
const province:ProvinceDefinition={slug:'fixture'}
const limits:FormLimits={maxRequests:'four',requestLength:300,factsLength:1200,maxEvidence:40}
const field:DocumentFieldDefinition={label:'Name',type:'text',maxLength:'300'}
useRegionDirectory(ref({province:'fixture',city:42,district:''}))
publicClient.versions({province:'fixture',district:'fixture'})
`
writeFileSync(new URL('negative.ts',scratch),negative)
const negativePath=fileURLToPath(new URL('negative.ts',scratch)),vitePath=root+'frontend/node_modules/vite/client.d.ts'
const negativeConfig=ts.parseJsonConfigFileContent({extends:root+'frontend/tsconfig.json',compilerOptions:{types:[]},files:[negativePath,vitePath],include:[]},ts.sys,fileURLToPath(scratch))
const negativeProgram=ts.createProgram(negativeConfig.fileNames,negativeConfig.options),negativeErrors=ts.getPreEmitDiagnostics(negativeProgram).filter(d=>d.file?.fileName.replaceAll('\\','/')===negativePath.replaceAll('\\','/'))
assert.equal(negativeErrors.length,5,ts.formatDiagnosticsWithColorAndContext(negativeErrors,{getCanonicalFileName:f=>f,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}))
assert(negativeErrors.every(d=>[2322,2345,2740].includes(d.code)),negativeErrors.map(d=>d.code).join(','))
console.log('PASS five genuine type counterexamples reject malformed province/field/capacity/directory/region inputs')
const files=[root+'frontend/node_modules/vite/client.d.ts',...owned.map(name=>fileURLToPath(new URL(`../frontend/src/${name}.vue`,import.meta.url)))]
writeFileSync(new URL('tsconfig.json',scratch),JSON.stringify({extends:root+'frontend/tsconfig.json',include:[],files,compilerOptions:{types:[]},vueCompilerOptions:{strictTemplates:true,dataAttributes:['data-*']}}))
const result=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',fileURLToPath(new URL('tsconfig.json',scratch)),'--noEmit'],{cwd:root,encoding:'utf8'})
assert.equal(result.status,0,(result.stdout+result.stderr).replaceAll(root,''))
console.log(`PASS public page types: ${owned.length} actual lang=ts components and strict Vue templates`)
