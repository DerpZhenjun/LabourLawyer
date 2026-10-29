import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import fs from 'node:fs'
import {useZhejiangOwnDrafts} from '../frontend/src/composables/useZhejiangOwnDrafts.js'
import {validateZhejiangOwn} from '../frontend/src/data/zhejiangOwnFields.js'
const require=createRequire(import.meta.url),{ref,nextTick}=require('../frontend/node_modules/vue')
const kind=ref('application'),own=ref(false),form=useZhejiangOwnDrafts(kind)
form.value.applicantName='虚构保留草稿'
// Actual route timing: kind changes while the guide is loading and adapter unknown.
kind.value='evidence';await nextTick();own.value=true;await nextTick()
assert.equal(validateZhejiangOwn(form.value,'evidence').valid,true)
assert.equal(Object.hasOwn(form.value,'requests'),false)
form.value.evidenceList[0].name='虚构保留的证据'
kind.value='application';await nextTick()
assert.equal(form.value.applicantName,'虚构保留草稿')
assert.equal(validateZhejiangOwn(form.value,'application').valid,true)
kind.value='evidence';await nextTick()
assert.equal(form.value.evidenceList[0].name,'虚构保留的证据')
const view=fs.readFileSync('frontend/src/views/RegionalDocument.vue','utf8')
assert.match(view,/const zhejiangOwnForm=useZhejiangOwnDrafts\(kind\)/)
assert.doesNotMatch(view,/watch\(kind/)
console.log('PASS async region/type navigation selects exact own draft and preserves both user drafts')
