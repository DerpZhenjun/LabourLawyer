import assert from 'node:assert/strict'
import fs from 'node:fs'
import {createRequire} from 'node:module'
const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const ts=require('typescript')
const {parse}=require('@vue/compiler-sfc')
const source=fs.readFileSync('frontend/src/views/RegionalGuide.vue','utf8')
const script=parse(source).descriptor.scriptSetup.content
const ast=ts.createSourceFile('RegionalGuide.ts',script,ts.ScriptTarget.Latest,true)
const node=ast.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text==='officialOnlineLink')
assert.ok(node,'The live view must resolve an explicit official entry or official guide fallback')
const code=ts.transpileModule(node.getText(ast),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText
const resolve=new Function(code+';return officialOnlineLink')()
const official='https://szcs.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=30'
assert.deepEqual(resolve(undefined,official),{href:official,direct:false})
assert.deepEqual(resolve('',official),{href:official,direct:false})
assert.deepEqual(resolve('https://www.jszwfw.gov.cn/login',official),{href:'https://www.jszwfw.gov.cn/login',direct:true})
for(const entry of ['javascript:alert(1)','/relative-entry','https://evil.example/entry','https://gov.cn.evil.example/entry','https://user:pass@portal.gov.cn/entry'])
 assert.equal(resolve(entry,official),null,entry)
for(const bad of [undefined,'','javascript:alert(1)','http://127.0.0.1:5176/province/jiangsu','https://evil.example/guide'])
 assert.equal(resolve(undefined,bad),null,String(bad))
assert.match(source,/v-if="onlineEntry"[^>]+:href="onlineEntry.href"/)
assert.match(source,/打开官方指南，核对在线入口/)
assert.doesNotMatch(source,/:href="guide.channel.entry_url"/)
console.log('PASS real view resolver: own official fallback, direct entry, unsafe and absent URLs produce no local CTA')
