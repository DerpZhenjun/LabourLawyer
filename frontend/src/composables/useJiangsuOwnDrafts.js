/** Keep own application/evidence drafts distinct across asynchronous guide changes. */
import {computed,ref} from 'vue'
import {createJiangsuOwnExample} from '../data/jiangsuOwnFields.js'
export function useJiangsuOwnDrafts(kind){
  const drafts={application:ref(createJiangsuOwnExample('application')),evidence:ref(createJiangsuOwnExample('evidence'))}
  const current=()=>drafts[kind.value==='evidence'?'evidence':'application']
  return computed({get:()=>current().value,set:value=>{current().value=value}})
}
