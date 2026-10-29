/** Keep own application/evidence drafts distinct across asynchronous guide changes. */
import {computed,ref} from 'vue'
import {createZhejiangOwnExample} from '../data/zhejiangOwnFields.js'
export function useZhejiangOwnDrafts(kind){
  const drafts={application:ref(createZhejiangOwnExample('application')),evidence:ref(createZhejiangOwnExample('evidence'))}
  const current=()=>drafts[kind.value==='evidence'?'evidence':'application']
  return computed({get:()=>current().value,set:value=>{current().value=value}})
}
