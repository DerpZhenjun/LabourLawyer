/** Keep untrusted own drafts distinct through asynchronous guide changes. */
import {computed,ref} from 'vue'
import type {Ref,WritableComputedRef} from 'vue'
import {createJiangsuOwnExample} from '../data/jiangsuOwnFields.ts'
export function useJiangsuOwnDrafts(kind: {readonly value: unknown}): WritableComputedRef<unknown>{
  const drafts: {application: Ref<unknown>; evidence: Ref<unknown>}={
    application:ref<unknown>(createJiangsuOwnExample('application')),
    evidence:ref<unknown>(createJiangsuOwnExample('evidence')),
  }
  const current=()=>drafts[kind.value==='evidence'?'evidence':'application']
  return computed<unknown>({get:()=>current().value,set:(value: unknown)=>{current().value=value}})
}
