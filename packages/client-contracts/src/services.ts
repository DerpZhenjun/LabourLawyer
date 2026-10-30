import {normalizeServiceAddress} from './index.ts'
import type {components} from './generated/stable-api'
type Status=components['schemas']['DigitalService']['status']
const statuses=['configured','not_configured','invalid_configuration'] as const satisfies readonly Status[]
export function configuredDigitalOrigin(value:unknown):string|null{
 if(!value||typeof value!=='object'||!('digital' in value)||!value.digital||typeof value.digital!=='object')throw Error('数字人服务配置格式不正确。')
 const digital=value.digital
 if(!('status' in digital)||!statuses.includes(digital.status as Status))throw Error('数字人服务配置状态不正确。')
 if(digital.status==='invalid_configuration')throw Error('数字人服务配置尚未通过检查，请联系服务维护人员。')
 if(digital.status!=='configured')return null
 if(!('url' in digital)||typeof digital.url!=='string')throw Error('数字人服务地址缺失。')
 return normalizeServiceAddress(digital.url)
}
