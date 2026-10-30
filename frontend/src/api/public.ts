/** Public read-only endpoints share the web/native transport boundary. */
import {readJSON} from './http.ts'
import {regionQuery} from '../../../packages/regional-contracts/src/index.ts'
import type {Region} from '../../../packages/regional-contracts/src/index.ts'
import {readAreaRows,readInventory,readRollout,readExperience,readCollectionReport,readVersions,record} from '../data/regionalGuidePresentation.ts'
const options=(signal?:AbortSignal):RequestInit=>signal?{signal}:{}
export const publicClient={
 async areas(province:string,city='',signal?:AbortSignal){const data=record(await readJSON(`/api/regional-guides/areas?province=${encodeURIComponent(province)}&city=${encodeURIComponent(city)}`,options(signal)));return readAreaRows(data.items,province,city)},
 async inventory(signal?:AbortSignal){return readInventory(await readJSON('/api/regional-guides/inventory',options(signal)))},
 async rollout(signal?:AbortSignal){return readRollout(await readJSON('/api/regional-guides/rollout-status',options(signal)))},
 async experience(slug:string,signal?:AbortSignal){return readExperience(await readJSON(`/api/portal-reports/experiences/${encodeURIComponent(slug)}`,options(signal)),slug)},
 async report(signal?:AbortSignal){const raw=await readJSON('/api/regional-guides/report',options(signal));return{raw,report:readCollectionReport(raw)}},
 async versions(region:Region,signal?:AbortSignal){return readVersions(await readJSON(`/api/regional-guides/versions?${regionQuery(region)}`,options(signal)))},
}
