/** A contract and every confirmation/download belong to one exact selection. */
import {computed,onBeforeUnmount,ref,shallowRef,watch} from 'vue'
import type {Ref} from 'vue'
import {assertFormContract,buildGenerateRequest,createExampleForm,isPlainRecord,validateForm} from '../../../packages/regional-contracts/src/index.ts'
import type {FormContext,FormContract,FormData,Validation} from '../../../packages/regional-contracts/src/index.ts'

interface FormClient {
  contract(context: FormContext,signal?: AbortSignal): Promise<FormContract>
  generate(contract: FormContract,raw: unknown,signal?: AbortSignal): Promise<Blob>
}
interface FormOptions {
  client: FormClient
  identity?: Readonly<Ref<string>>
  example?: (contract: FormContract)=>unknown
  validateSpecial?: (contract: FormContract,raw: unknown)=>Validation
  filename?: (contract: FormContract)=>string
  download: (blob: Blob,filename: string)=>Promise<void> | void
}
interface Confirmation {
  selection: number; revision: number; scope: string; contract: FormContract; data: FormData
}

// Unlike JSON roundtripping or object spread, this retains hidden/symbol keys,
// array extras and holes. Invalid drafts stay invalid instead of losing data.
function copyRaw(value: unknown): unknown {
  if(Array.isArray(value)) {
    const result: unknown[]=new Array(value.length)
    for(const key of Reflect.ownKeys(value))if(key!=='length')Object.defineProperty(result,key,{value:copyRaw(Reflect.get(value,key)),enumerable:true,writable:true,configurable:true})
    return result
  }
  if(isPlainRecord(value))return Object.fromEntries(Reflect.ownKeys(value).map(key=>[key,copyRaw(Reflect.get(value,key))]))
  return value
}
const message=(error: unknown,fallback: string)=>error instanceof Error?error.message:fallback
const defaultFilename=(contract: FormContract)=>`${contract.context.district}-${contract.context.kind==='evidence'?'证据清单':'仲裁申请书'}-${contract.context.adapter.startsWith('hunan_own_legacy_worker')?'官方DOC转换填写':contract.context.mode==='blank'?'空白表格填写':'参考填写'}.docx`

export function useRegionalForm(context: Readonly<Ref<FormContext|null>>,options: FormOptions) {
  const contract=shallowRef<FormContract|null>(null),raw=ref<unknown>(undefined),draftKey=ref('')
  const loading=ref(false),error=ref(''),generationError=ref(''),generating=ref(false),downloaded=ref(false),confirmOpen=ref(false)
  const confirmationAction=shallowRef<(()=>Promise<boolean>)|undefined>(undefined)
  const drafts=new Map<string,unknown>()
  let selection=0,generation=0,revision=0,loadedScope='',confirmation: Confirmation|null=null,disposed=false
  let loadingController: AbortController|undefined,generationController: AbortController|undefined
  const scope=computed(()=>{
    const c=context.value
    return JSON.stringify([c?[c.province,c.city,c.district,c.region_code,c.source_id,c.version,c.template_id,c.kind,c.mode,c.adapter]:null,options.identity?.value??''])
  })

  function cancelConfirmation() { confirmation=null;confirmationAction.value=undefined;confirmOpen.value=false }
  function invalidateGeneration() {
    ++generation;generationController?.abort();generationController=undefined
    generating.value=false;downloaded.value=false;cancelConfirmation()
  }
  watch(raw,()=>{
    ++revision
    if(draftKey.value)drafts.set(draftKey.value,copyRaw(raw.value))
    invalidateGeneration();generationError.value=''
  },{deep:true,flush:'sync'})
  const draft=computed<unknown>({get:()=>raw.value,set:(value: unknown)=>{raw.value=value}})
  const ready=computed(()=>!disposed&&!loading.value&&contract.value!==null&&loadedScope===scope.value&&context.value!==null)
  const validation=computed<Validation>(()=>{
    if(!ready.value||!contract.value)return{valid:false,errors:[]}
    const shared=validateForm(contract.value,raw.value)
    const special=options.validateSpecial?.(contract.value,raw.value)
    return special?{valid:shared.valid&&special.valid,errors:[...shared.errors,...special.errors]}:shared
  })

  async function reload(): Promise<void> {
    if(disposed)return
    const ticket=++selection,currentScope=scope.value,selected=context.value
    if(draftKey.value)drafts.set(draftKey.value,copyRaw(raw.value))
    loadingController?.abort();invalidateGeneration()
    contract.value=null;loadedScope='';draftKey.value='';raw.value=undefined;loading.value=false;error.value='';generationError.value=''
    if(!selected)return
    const expected={...selected},controller=new AbortController();loadingController=controller;loading.value=true
    try {
      const result=assertFormContract(await options.client.contract(expected,controller.signal),expected)
      if(disposed||ticket!==selection||currentScope!==scope.value||controller.signal.aborted)return
      const key=JSON.stringify([currentScope,result.contract_id])
      const value=drafts.has(key)?copyRaw(drafts.get(key)):options.example?options.example(result):createExampleForm(result)
      draftKey.value=key;raw.value=value;loadedScope=currentScope;contract.value=result
    } catch(cause: unknown) {
      if(!disposed&&ticket===selection&&currentScope===scope.value&&!controller.signal.aborted)
        error.value=message(cause,'无法核对本区表单，请重试。')
    } finally {
      if(!disposed&&ticket===selection&&currentScope===scope.value)loading.value=false
    }
  }
  function requestConfirmation(): boolean {
    generationError.value='';downloaded.value=false
    if(!ready.value||!contract.value||generating.value){generationError.value='请先等待本区表单核对完成。';return false}
    const checked=validation.value
    if(!checked.valid){generationError.value=checked.errors.map(e=>e.message).join('；')||'请核对填写内容。';return false}
    try {
      // Make known hidden fields enumerable only after retaining and validating
      // every raw key, so the portable JSON request builder cannot omit a slot.
      const request=buildGenerateRequest(contract.value,copyRaw(raw.value))
      const approved={selection,revision,scope:scope.value,contract:contract.value,data:request.data}
      confirmation=approved;confirmationAction.value=()=>generateApproved(approved)
      confirmOpen.value=true;return true
    } catch(cause: unknown) {generationError.value=message(cause,'请核对填写内容。');return false}
  }
  async function generateApproved(approved: Confirmation|null): Promise<boolean> {
    const current=()=>!disposed&&approved!==null&&approved.selection===selection&&approved.revision===revision&&approved.scope===scope.value&&ready.value&&contract.value?.contract_id===approved.contract.contract_id
    if(!approved||confirmation!==approved||!current()||generating.value)return false
    cancelConfirmation();generationError.value='';downloaded.value=false;generating.value=true
    const ticket=++generation,controller=new AbortController();generationController=controller
    const active=()=>ticket===generation&&!controller.signal.aborted&&current()
    try {
      const blob=await options.client.generate(approved.contract,approved.data,controller.signal)
      if(!active())return false
      await options.download(blob,(options.filename??defaultFilename)(approved.contract))
      if(!active())return false
      downloaded.value=true;return true
    } catch(cause: unknown) {
      if(active())generationError.value=message(cause,'无法生成，请核对内容后重试。')
      return false
    } finally {
      if(ticket===generation&&!disposed){generating.value=false;generationController=undefined}
    }
  }
  const generate=()=>generateApproved(confirmation)
  watch(scope,()=>{void reload()},{immediate:true,flush:'sync'})
  onBeforeUnmount(()=>{
    disposed=true;++selection;loadingController?.abort();invalidateGeneration();drafts.clear()
  })
  return{contract,draft,draftKey,loading,error,generationError,generating,downloaded,confirmOpen,confirmationAction,validation,ready,reload,requestConfirmation,cancelConfirmation,generate}
}
