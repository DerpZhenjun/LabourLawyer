import { createRouter, createWebHistory } from 'vue-router'
import type {RouteRecordRaw,RouteMeta} from 'vue-router'
import { findProvince } from '@/data/provinces'
import PublicHome from '@/views/PublicHome.vue'
import {verifySession} from '@/api/auth'
const ConnectionSettings=()=>import('@/views/ConnectionSettings.vue')
const Login=()=>import('@/views/Login.vue')
const ProvinceGuide = () => import('@/views/ProvinceGuide.vue')
const RegionalGuide = () => import('@/views/RegionalGuide.vue')
const RegionalDocument = () => import('@/views/RegionalDocument.vue')
const RegionalCollection = () => import('@/views/RegionalCollection.vue')
const Dashboard = () => import('@/views/Dashboard.vue')
const CaseCenter = () => import('@/views/CaseCenter.vue')
const EvidenceCenter = () => import('@/views/EvidenceCenter.vue')
const DocumentCenter = () => import('@/views/DocumentCenter.vue')
const DeadlineCenter = () => import('@/views/DeadlineCenter.vue')
const KnowledgeCenter = () => import('@/views/KnowledgeCenter.vue')
const ZhejiangLA = () => import('@/views/Zhejiang/LA.vue')
const ZhejiangEL = () => import('@/views/Zhejiang/EL.vue')

const adminMeta = (eyebrow:string, title:string):RouteMeta => ({ layout: 'admin', eyebrow, title })

const routes:RouteRecordRaw[] = [
  {path:'/admin/collector',component:()=>import('@/views/OfficialCollector.vue'),meta:adminMeta('公开资料采集','官方指南采集')},
  {path:'/connection',component:ConnectionSettings,meta:{title:'连接服务'}},
  {path:'/login',name:'login',component:Login,meta:{title:'登录工作区'}},
  { path: '/', name: 'public-home', component: PublicHome, meta: { title: '劳动仲裁文书助手' } },
  { path: '/province/:slug', name: 'province-guide', component: RegionalGuide, meta: { title: '按地区查劳动仲裁指南' } },
  { path: '/province/:slug/templates', name: 'province-template-scope', component: ProvinceGuide, meta: { title: '已收录文书的适用范围' } },
  { path: '/local-documents/:slug/:kind(application|evidence)', component: RegionalDocument, meta: { title: '当地文书辅助填写' } },
  { path: '/documents/:province/application', component: ZhejiangLA, props: route => ({ province: route.params.province }), meta: { title: '劳动仲裁申请书' } },
  { path: '/documents/:province/evidence', component: ZhejiangEL, props: route => ({ province: route.params.province }), meta: { title: '劳动仲裁证据清单' } },

  { path: '/admin', name: 'admin-dashboard', component: Dashboard, meta: adminMeta('数据概览', '管理后台') },
  { path: '/admin/cases', name: 'admin-cases', component: CaseCenter, meta: adminMeta('案件管理', '案件中心') },
  { path: '/admin/evidence', name: 'admin-evidence', component: EvidenceCenter, meta: adminMeta('材料管理', '证据中心') },
  { path: '/admin/documents', name: 'admin-documents', component: DocumentCenter, meta: adminMeta('模板与生成', '文书管理') },
  { path: '/admin/deadlines', name: 'admin-deadlines', component: DeadlineCenter, meta: adminMeta('时效管理', '时效与日程') },
  { path: '/admin/knowledge', name: 'admin-knowledge', component: KnowledgeCenter, meta: adminMeta('内容管理', '法规知识库') },
  { path: '/admin/regions', name: 'admin-regions', component: RegionalCollection, meta: adminMeta('官方来源核验', '地区采集与问题记录') },

  { path: '/documents', redirect: '/' },
  { path: '/cases', redirect: '/admin/cases' },
  { path: '/evidence', redirect: '/admin/evidence' },
  { path: '/deadlines', redirect: '/admin/deadlines' },
  { path: '/knowledge', redirect: '/admin/knowledge' },
  { path: '/zhejiang/la', redirect: '/documents/zhejiang/application' },
  { path: '/zhejiang/el', redirect: '/documents/zhejiang/evidence' },
  { path: '/guangdong/la', redirect: '/documents/guangdong/application' },
  { path: '/guangdong/el', redirect: '/documents/guangdong/evidence' },
]

const router=createRouter({history:createWebHistory(import.meta.env.BASE_URL),routes,scrollBehavior(to){return to.hash?{el:to.hash,behavior:'smooth'}:{top:0}}})
router.beforeEach(async to => {
  if(to.meta.layout==='admin'){
    try{const user=await verifySession();if(!user||user.role!=='admin')return{path:'/login',query:{next:to.fullPath}}}
    catch{return{path:'/login',query:{next:to.fullPath}}}
  }
  if (to.path.startsWith('/documents/') && to.params.province) {
    const province = findProvince(typeof to.params.province==='string'?to.params.province:'')
    const kind = to.path.endsWith('/evidence') ? 'hasEvidence' : 'hasApplication'
    if (!province) return '/'
    const ownsScope = Object.hasOwn(to.query, 'city') || Object.hasOwn(to.query, 'district')
    if (ownsScope) {
      const complete = ['city', 'district'].every(key => typeof to.query[key] === 'string' && to.query[key].trim())
      const documentKind = kind === 'hasEvidence' ? 'evidence' : 'application'
      return { path: complete ? `/local-documents/${province.slug}/${documentKind}` : `/province/${province.slug}`, query: to.query, hash: to.hash }
    }
    if (!province[kind]) return `/province/${province.slug}`
  }
})
router.afterEach(to=>{document.title=to.meta.title?`${to.meta.title} · LabourLawyer`:'LabourLawyer · 劳动仲裁文书助手'})
export default router
