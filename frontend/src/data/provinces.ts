import type {DocumentFieldDefinition,FormLimits,FormSchema} from '../../../packages/client-contracts/src/documents'
export type {DocumentFieldDefinition,FormLimits} from '../../../packages/client-contracts/src/documents'
import formSchema from '../../../config/document_forms.json' with {type:'json'}
import officialCatalog from './provinceCatalog.json' with {type:'json'}


export interface ProcessStep {title:string; text:string}
interface LocalDetails {city:string;committee:string;company:string;submission:string;materialNote:string;copyHint:string;promise?:string}
export interface ProvinceDefinition extends Omit<(typeof officialCatalog)[number],'status'> {
 shortName:string;status:'ready'|'guide';officialUrl:string;officialName:string;searchKeyword:string
 applicationRoute:string|null;evidenceRoute:string|null;note:string;process:ProcessStep[]
 materials:string[]|undefined;materialNote:string|undefined;copyHint:string|undefined;promise:string
 city:string|undefined;committee:string|undefined;exampleCompany:string|undefined
}
export type Province=ProvinceDefinition
const typedSchema:FormSchema=formSchema

const shortNames:Record<string,string> = {
  beijing:'北京',tianjin:'天津',hebei:'河北',shanxi:'山西',neimenggu:'内蒙古',liaoning:'辽宁',jilin:'吉林',heilongjiang:'黑龙江',
  shanghai:'上海',jiangsu:'江苏',zhejiang:'浙江',anhui:'安徽',fujian:'福建',jiangxi:'江西',shandong:'山东',henan:'河南',hubei:'湖北',hunan:'湖南',
  guangdong:'广东',guangxi:'广西',hainan:'海南',chongqing:'重庆',sichuan:'四川',guizhou:'贵州',yunnan:'云南',xizang:'西藏',
  shaanxi:'陕西',gansu:'甘肃',qinghai:'青海',ningxia:'宁夏',xinjiang:'新疆',
}

const localDetails:Record<string,LocalDetails> = {
  shanxi:{city:'太原市',committee:'',company:'山西测试科技有限公司',submission:'先确认由哪个仲裁机构受理。填好申请书，打印后本人签名并捺印。',materialNote:'带上申请书、身份证复印件和支持请求的证据。',copyHint:'申请书副本按被申请人人数准备；证据份数向受理机构确认。'},
  beijing:{city:'北京市朝阳区',committee:'北京市朝阳区劳动人事争议仲裁委员会',company:'北京朝阳启明科技有限公司',submission:'来源页提供朝阳区立案材料压缩包，模板注明申请书通常一式四份，证据复印件一式两份并在开庭时携带原件。',materialNote:'申请书、身份证件复印件、证据材料清单及证据复印件。证据应编号并注明是否有原件。',copyHint:'朝阳区模板注明申请书通常一式四份；共同当事人时按模板说明增加。'},
  tianjin:{city:'天津市滨海新区',committee:'天津市滨海新区劳动人事争议仲裁委员会',company:'天津滨海远航科技有限公司',submission:'来源和模板适用于中新天津生态城及滨海新区场景；申请前应向实际工作地或单位所在地的仲裁机构确认管辖。',materialNote:'模板要求单位名称与市场主体信息一致，并填写文书邮寄送达地址。',copyHint:'申请书和证据份数应按受理机构及对方当事人人数核对。'},
  neimenggu:{city:'鄂尔多斯市',committee:'鄂尔多斯市劳动人事争议仲裁委员会',company:'鄂尔多斯市恒川商贸有限公司',submission:'当前官方申请书来自鄂尔多斯市劳动人事争议仲裁院，其他盟市提交前应下载当地最新版本核对。',materialNote:'申请书包含户籍所在地、现住址、公司统一社会信用代码及第三人信息。',copyHint:'按被申请人及第三人人数准备申请书副本。'},
  liaoning:{city:'沈阳市',committee:'沈阳市劳动人事争议仲裁委员会',company:'沈阳华辰信息技术有限公司',submission:'辽宁政务服务网指南提供仲裁申请书下载；模板要求请求简明，并写清劳动关系建立和争议发生过程。',materialNote:'申请书、身份证明、公司主体信息、劳动关系和请求依据材料。',copyHint:'辽宁模板注明申请书副本按被申请人数加一份提交。'},
  jiangsu:{city:'无锡市锡山区',committee:'无锡市锡山区劳动人事争议仲裁委员会',company:'无锡锡山云帆科技有限公司',submission:'当前模板来自江苏政务服务网锡山区事项页，表内需选择是否接受调解、是否申请法律援助。',materialNote:'除身份和主体材料外，模板单列调解意愿、法律援助和送达地址信息。',copyHint:'按事项页面和具体受理机构要求准备申请书及证据副本。'},
  zhejiang:{city:'杭州市',committee:'杭州市劳动人事争议仲裁委员会',company:'杭州星河网络科技有限公司',submission:'可到仲裁委员会提交、邮寄，或通过“浙里办”中的智慧仲裁办理；官方事项页显示现场办理次数为 0。',materialNote:'官方事项页列有用人单位登记材料、劳动者身份证、申请书、证据清单和支持请求的证据。',copyHint:'浙江官方事项页所列材料通常标注为 A4、原件、2 份。',promise:'44 个工作日'},
  fujian:{city:'福州市',committee:'福建省劳动人事争议仲裁委员会',company:'福州海岳数字科技有限公司',submission:'福建官方说明支持通过福建人社、闽政通或网上办事大厅预申请，最终以有管辖权的仲裁委员会要求为准。',materialNote:'模板要求事实理由写明劳动关系建立、争议发生事实及请求依据，并及时书面更新送达地址。',copyHint:'申请书副本按被申请人和第三人人数提交。'},
  jiangxi:{city:'赣州市',committee:'赣州市劳动人事争议仲裁委员会',company:'赣州青峰电子商务有限公司',submission:'当前官方模板来自赣州市人社局，申请书和证据目录均要求按被申请人人数增加副本。',materialNote:'证据目录明确将申请人身份证、被申请人营业执照或企业公示信息列为前两项材料。',copyHint:'模板注明申请书和证据材料一式两份，并按被申请人人数增加副本。'},
  shandong:{city:'淄博市',committee:'淄博市劳动人事争议仲裁委员会',company:'淄博齐盛新材料有限公司',submission:'当前模板来自淄博市人社局；申请书附件栏需要填写申请书副本及证据材料份数。',materialNote:'申请书、身份证明、用人单位主体信息、证据清单及相关证据。',copyHint:'按被申请人及第三人人数核对申请书和证据材料份数。'},
  henan:{city:'平顶山市',committee:'平顶山市劳动人事争议仲裁委员会',company:'平顶山中原智造有限公司',submission:'当前申请书来自平顶山市人社局，页面未提供单独的可编辑证据清单。',materialNote:'申请书、身份证明、企业登记材料以及支持每项请求的证据。',copyHint:'申请书附件栏要求填写副本和证据材料份数。'},
  hubei:{city:'武汉市',committee:'武汉市劳动人事争议仲裁委员会',company:'武汉东湖创联科技有限公司',submission:'湖北来源文件是全省劳动人事争议仲裁文书标准，在线生成使用其中劳动者申请书和证据目录格式。',materialNote:'湖北标准要求申请书写明当事人信息、具体请求及金额、事实理由、证据来源和证人信息。',copyHint:'申请书及证据除正本外，按被申请人人数提交副本。'},
  hunan:{city:'岳阳市',committee:'岳阳市劳动人事争议仲裁委员会',company:'岳阳洞庭物流有限公司',submission:'当前模板来自岳阳市人社局，表格和落款中已明确当地仲裁委员会名称。',materialNote:'证据清单单列页码范围、原件或复印件、来源和证明目的。',copyHint:'按当地窗口通知及对方当事人人数准备副本。'},
  guangdong:{city:'广州市',committee:'广州市劳动人事争议仲裁委员会',company:'广州南辰科技有限公司',submission:'支持网上或窗口办理。省级事项链接主要对应省级受理范围，多数案件应向实际工作地或单位所在地的市、区仲裁委员会申请。',materialNote:'申请书需写明请求期间、金额和计算方法，并提交身份证明、公司登记材料及证据。',copyHint:'广东官方页面将证据材料列为 2 份，申请书副本按被申请人及第三人人数提交。',promise:'5 个工作日内决定是否受理'},
  hainan:{city:'三亚市',committee:'三亚市劳动人事争议仲裁委员会',company:'三亚海蓝文旅有限公司',submission:'当前模板来自三亚市人社局，申请书包含劳动合同、岗位、工资、考勤、加班和解除情况等详细事实字段。',materialNote:'模板提示打印版申请书按当事人数加一份，并附基本表、身份证复印件和企业登记资料。',copyHint:'三亚模板提示申请书通常一式三份，并按当事人数 n+1 调整。'},
  sichuan:{city:'广元市',committee:'广元市劳动人事争议仲裁委员会',company:'广元蜀道商贸有限公司',submission:'当前模板由广元市劳动人事争议仲裁委员会发布，其他市州应先核对当地模板。',materialNote:'申请书单列确认有效通讯地址、邮政编码、第三人和委托代理人信息。',copyHint:'按照被申请人、第三人人数及受理机构通知准备副本。'},
  guizhou:{city:'遵义市',committee:'遵义市劳动人事争议仲裁委员会',company:'遵义黔北供应链有限公司',submission:'当前模板来自贵州政务服务网遵义市事项，其他市州应在当地政务服务事项中核对。',materialNote:'申请书要求填写原籍、现住址、确认有效通讯地址、邮编及第三人信息。',copyHint:'申请书副本按被申请人和第三人人数准备。'},
  yunnan:{city:'昆明市呈贡区',committee:'昆明市呈贡区劳动人事争议仲裁委员会',company:'昆明呈贡云创科技有限公司',submission:'当前官方文件来自昆明市呈贡区，申请书和证据清单在同一个附录文件中。',materialNote:'合并模板要求填写通讯地址及邮编、统一社会信用代码、请求、事实理由和证据清单。',copyHint:'模板注明申请书及证据材料按被申请人数量提交副本。'},
  shaanxi:{city:'西安市高新区',committee:'西安市劳动人事争议仲裁委员会高新区派出庭',company:'西安高新秦创科技有限公司',submission:'当前模板适用于西安高新区派出庭，其他区县应按所在地仲裁机构最新要求办理。',materialNote:'请求应明确具体、分项列明并合计金额；同时提交身份证复印件。',copyHint:'陕西高新区模板注明申请书副本按被申请人数加一份。'},
  gansu:{city:'白银市',committee:'白银市劳动人事争议仲裁委员会',company:'白银陇原新能源有限公司',submission:'当前模板来自白银市人社局，页面仅提供申请书，没有单独证据清单。',materialNote:'事实理由应包含入职、解除或终止、岗位、工资构成、证据来源及证人信息。',copyHint:'甘肃模板注明申请书副本按被申请人数提交。'},
  xinjiang:{city:'乌鲁木齐市',committee:'新疆维吾尔自治区劳动人事争议仲裁委员会',company:'新疆天山数字科技有限公司',submission:'新疆来源文件是自治区人社厅发布的申请书范例，生成后仍应删除不适用的范例项目并核对最新要求。',materialNote:'注意事项要求写明请求项目、数额和起止时间，并提交身份证、劳动关系证明、企业登记资料及相关证据。',copyHint:'按申请人与被申请人人数提交申请书，所有材料使用 A4 纸。'},
}

const pendingDetails:Record<string,string> = {
  hebei:'官方公共服务平台可查询和办理事项，目前未发现可直接下载的公开空白 Word 模板。',
  shanxi:'已取得并验证山西省级平台的申请书，可在线填写。',
  jilin:'官方指南已收录，尚未发现可直接下载的公开空白 Word 模板。',
  heilongjiang:'官方页面提供办事说明和线上服务入口，尚未发现公开空白 Word 模板。',
  shanghai:'官方来源提供 PDF 表格，当前尚未转换为经验证的可填充 Word 模板。',
  anhui:'铜陵市官方页面提供办理说明，尚未发现公开空白 Word 模板。',
  guangxi:'已取得自治区官方办事指南 PDF，尚未取得单独空白申请书和证据清单。',
  chongqing:'重庆市人社局提供劳动关系服务指南，尚未发现公开空白 Word 模板。',
  xizang:'自治区人社厅官方指南已收录，尚未发现公开空白 Word 模板。',
  qinghai:'已取得湟源县官方办事指南 PDF，尚未取得单独空白 Word 模板。',
  ningxia:'已取得自治区人社厅官方指南文件，尚未发现公开空白 Word 模板。',
}

const makeProcess = (item:(typeof officialCatalog)[number]):ProcessStep[] => {
  const local = localDetails[item.slug]
  if (!local) return [
    {title:'查看官方指南',text:`打开${item.authority}发布的页面，确认当前办理入口、管辖和材料要求。`},
    {title:'确认受理机构',text:'一般向实际工作地或用人单位所在地的劳动人事争议仲裁委员会申请。'},
    {title:'准备申请材料',text:'在取得当地最新空白模板后填写申请书，并整理身份证明、主体信息和证据。'},
    {title:'提交并等待通知',text:'按照官方页面选择线上或窗口提交，并留意补正、调解和开庭通知。'},
  ]
  return [
    {title:'先核对适用范围',text:`当前模板来源为${item.authority}，标明适用范围是${item.scope}。不在该范围时先向当地仲裁机构确认。`},
    {title:'按官方模板填写',text:local.submission},
    {title:'整理并提交材料',text:local.materialNote},
    {title:'等待审查和后续通知',text:'提交后留意受理、一次性补正、调解或开庭通知；具体期限和方式以实际受理机构最新通知为准。'},
  ]
}

export const buildProvinceDefinitions = (catalog:typeof officialCatalog):ProvinceDefinition[] => catalog.map(item => {
  const shortName=shortNames[item.slug]??item.name
  const ready=item.hasApplication||item.hasEvidence
  const local=localDetails[item.slug]
  return {
    ...item,shortName,status:ready?'ready':'guide',officialUrl:item.source_url,officialName:item.authority,
    searchKeyword:'劳动人事争议仲裁申请',
    applicationRoute:item.hasApplication?`/documents/${item.slug}/application`:null,
    evidenceRoute:item.hasEvidence?`/documents/${item.slug}/evidence`:null,
    note:local?.submission||pendingDetails[item.slug]||'已记录官方事项来源，模板取得并验证后开放在线生成。',
    process:makeProcess(item),
    materials:local?['有效身份证件及复印件','用人单位登记信息或企业信用信息',item.hasApplication?'填写并签名的官方仲裁申请书':'当地仲裁机构要求的仲裁申请书',item.hasEvidence?'按官方证据清单整理的证据材料':'能够证明劳动关系和支持请求的证据材料','委托他人办理时所需的授权委托材料']:undefined,
    materialNote:local?.materialNote,copyHint:local?.copyHint,promise:local?.promise||'以受理机构通知为准',
    city:local?.city,committee:local?.committee,exampleCompany:local?.company,
  }
})

export const provinces:ProvinceDefinition[] = buildProvinceDefinitions(officialCatalog)

export const provinceGroups = ['华东', '华南', '华北', '华中', '东北', '西南', '西北']
export const commonMaterials = ['仲裁申请书：本人签字，并按被申请人人数准备副本','身份证明：身份证复印件；委托办理还需授权委托书','劳动关系证明：劳动合同、工资流水、社保记录、工牌等','支持仲裁请求的证据，并附上按顺序整理的证据清单','用人单位主体信息：企业名称、统一社会信用代码和注册地址']
export const commonProcess = [{title:'确认管辖',text:'一般向实际工作地或用人单位所在地的劳动人事争议仲裁委员会申请。'},{title:'准备材料',text:'填写仲裁申请书，整理身份证明、劳动关系证明、证据和证据清单。'},{title:'线上或现场申请',text:'通过当地政务服务网提交，或前往有管辖权的仲裁委员会窗口办理。'},{title:'等待受理',text:'仲裁委员会收到申请后依法审查；材料不完整的，会通知补正。'},{title:'调解或开庭',text:'受理后可能先行调解；未达成调解的，依法安排开庭并作出裁决。'}]

const identityPrefixes:Record<string,string>={beijing:'110105',tianjin:'120116',neimenggu:'150602',liaoning:'210102',jiangsu:'320205',zhejiang:'330102',fujian:'350102',jiangxi:'360702',shandong:'370303',henan:'410402',hubei:'420106',hunan:'430602',guangdong:'440106',hainan:'460204',sichuan:'510802',guizhou:'520302',yunnan:'530114',shaanxi:'610190',gansu:'620402',xinjiang:'650102'}
const examplePostalCodes:Record<string,string>={beijing:'100020',tianjin:'300450',neimenggu:'017000',liaoning:'110000',jiangsu:'214000',zhejiang:'310000',fujian:'350000',jiangxi:'341000',shandong:'255000',henan:'467000',hubei:'430000',hunan:'414000',guangdong:'510000',hainan:'572000',sichuan:'628000',guizhou:'563000',yunnan:'650500',shaanxi:'710000',gansu:'730900',xinjiang:'830000'}
export const makeApplicationExample = (province:ProvinceDefinition) => {
  const city=province.city||province.shortName,applicant=province.slug==='guangdong'?'李娜':'王晨'
  return {committeeName:province.committee||`${city}劳动人事争议仲裁委员会`,applicantName:applicant,birthDate:'1992-08-16',gender:applicant==='李娜'?'女':'男',nationality:'汉族',idNumber:`${identityPrefixes[province.slug]||'110101'}199208160015`,phone:'13800001234',householdType:'本省非农业户口',idAddress:`${city}人民路88号`,applicantMailingAddress:`${city}人民路88号`,respondentName:province.exampleCompany||`${province.shortName}启明科技有限公司`,socialCreditCode:'91320100MA2B12345X',registeredAddress:`${city}创新大道120号`,mailingAddress:`${city}创新大道120号`,workAddress:`${city}创新大道120号8层`,legalRepName:'张明',legalRepPhone:'13900005678',legalRepPosition:'执行董事',companyContact:'刘婷',companyContactPhone:'13900005678',requests:['请求被申请人支付2026年6月至8月拖欠的工资共计24000元。','请求被申请人支付解除劳动合同经济补偿20000元。'],claimCalculation:'拖欠工资：8000元/月×3个月＝24000元；经济补偿：8000元/月×2.5个月＝20000元。',employmentDate:'2024-04-01',jobTitle:'产品运营',signedContract:'有',contractStartDate:'2024-04-01',contractEndDate:'2027-03-31',workSchedule:'每周工作5天，每天工作8小时',attendanceRequired:'是',attendanceMethod:'企业微信打卡',salaryPaymentMethod:'转账',salaryReceiptRequired:'不需要签收',startingSalary:'8000',salaryAdjustments:'无',currentlyEmployed:'否',departureDate:'2026-08-31',departureReason:'双方经公司提出协商一致解除劳动合同，公司未支付约定经济补偿',averageMonthlySalary:'8000',currentAddress:`${city}人民路88号`,applicantPostalCode:examplePostalCodes[province.slug],respondentPostalCode:examplePostalCodes[province.slug],nativePlace:city,identityDocumentType:'居民身份证',acceptMediation:'是',legalAid:'否',respondentType:'有限责任公司',departmentHead:'赵磊',departmentHeadPosition:'运营主管',officeAtRegisteredAddress:'是',actualOfficeAddress:`${city}创新大道120号8层`,occupation:'产品运营',employmentType:'合同制',registeredCapital:'100万元',lastWorkingDate:'2026-08-31',otherNotes:'无' ,factsReason:`申请人${applicant}于2024年4月1日入职被申请人，担任产品运营，双方约定月工资8000元。申请人一直正常提供劳动，被申请人自2026年6月起未按约支付工资，并于2026年8月31日提出并与申请人协商一致解除劳动合同，未支付拖欠工资及经济补偿。申请人多次与公司沟通无果，现依法申请仲裁。`,copyCount:2,applicationDate:'2026-09-23'}
}
export const makeEvidenceExample = (province:ProvinceDefinition) => {
  const application=makeApplicationExample(province)
  const identityItems=province.slug==='jiangxi'?[{name:'申请人身份证复印件',pageCount:'1页',source:'本人提供',purpose:'证明申请人的主体资格。'},{name:'被申请人企业信用信息公示报告',pageCount:'3页',source:'国家企业信用信息公示系统',purpose:'证明被申请人的主体资格及登记信息。'}]:[]
  const result={committeeName:application.committeeName,caseNumber:'',copyCount:2,submitterName:application.applicantName,submitDate:'2026-09-23',evidenceList:[...identityItems,{name:'劳动合同',pageCount:'5页',source:'本人保存',purpose:'证明申请人与被申请人自2024年4月1日起存在劳动关系，约定岗位和工资标准。'},{name:'2026年6月至8月银行工资流水',pageCount:'3页',source:'手机银行下载',purpose:'证明被申请人未支付2026年6月至8月工资。'},{name:'解除通知及沟通记录',pageCount:'6页',source:'本人手机导出',purpose:'证明被申请人于2026年8月31日解除劳动关系及双方沟通过程。'}]}
  let page=1
  const evidenceList=result.evidenceList.map((item,index)=>{const count=parseInt(item.pageCount)||1;const start=page;page+=count;return {...item,kind:index===result.evidenceList.length-1?'电子数据':'书证',originalType:'复印件',hasOriginal:'有',pageRange:`第${start}页至第${page-1}页`,itemCount:'1',notes:'原件或原始载体备查'}})
  return {...result,evidenceList}
}
export const findProvince = (slug:unknown):ProvinceDefinition|undefined => provinces.find(item => item.slug === slug)
export type ApplicationExample=ReturnType<typeof makeApplicationExample>&Record<string,unknown>
export type EvidenceExample=ReturnType<typeof makeEvidenceExample>&Record<string,unknown>


// Extra inputs exist only where the retained official form has these slots.
const fieldPairs=(source:Record<string,string[][]>):Record<string,[string,string][]>=>Object.fromEntries(Object.entries(source).map(([slug,fields])=>[slug,fields.map((pair):[string,string]=>{
  const [key,label]=pair
  if(pair.length!==2||key===undefined||label===undefined)throw new Error('文书栏目配置格式不正确')
  return[key,label]
})]))
export const applicationExtraFields = fieldPairs(typedSchema.applicationExtraFields)
export const evidenceExtraFields = fieldPairs(typedSchema.evidenceExtraFields)
export const applicationSupportedFields = typedSchema.applicationSupportedFields
export const evidenceSupportedFields = typedSchema.evidenceSupportedFields
export const documentFormLimits = (slug:string):FormLimits => typedSchema.limits[slug] || typedSchema.limits.default
export const documentFieldDefinitions = typedSchema.fields
