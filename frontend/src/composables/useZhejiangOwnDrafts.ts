/** Keep untrusted own drafts distinct through asynchronous guide changes. */
import {computed,ref} from 'vue'
import type {Ref,WritableComputedRef} from 'vue'
import {createZhejiangOwnExample} from '../data/zhejiangOwnFields.ts'
export function useZhejiangOwnDrafts(kind: {readonly value: unknown}): WritableComputedRef<unknown>{
  const drafts: {application: Ref<unknown>; evidence: Ref<unknown>}={
    application:ref<unknown>(createZhejiangOwnExample('application')),
    evidence:ref<unknown>(createZhejiangOwnExample('evidence')),
  }
  const current=()=>drafts[kind.value==='evidence'?'evidence':'application']
  return computed<unknown>({get:()=>current().value,set:(value: unknown)=>{current().value=value}})
}
