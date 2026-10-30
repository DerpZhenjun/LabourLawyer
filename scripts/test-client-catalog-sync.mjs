import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {readFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {buildProvinceDefinitions} from '../frontend/src/data/provinces.ts'
const root=new URL('../',import.meta.url)
const names=['frontend/src/data/provinceCatalog.json','miniprogram/data/documentForms.json','miniprogram/data/provinces.json']
const before=names.map(name=>readFileSync(new URL(name,root)))
execFileSync(process.execPath,[fileURLToPath(new URL('./sync-document-clients.mjs',import.meta.url)),'--check'],{stdio:'inherit'})
names.forEach((name,i)=>assert(before[i].equals(readFileSync(new URL(name,root))),'Check must not rewrite snapshots'))
const catalog=JSON.parse(before[0].toString())
catalog[0].authority='仅测试：更新后的机关'
const updated=buildProvinceDefinitions(catalog)
assert.equal(updated[0].officialName,catalog[0].authority,'Synchronization must enrich fresh backend metadata rather than the old imported snapshot')
console.log('PASS real typed catalog builder and read-only client snapshot parity')
