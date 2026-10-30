# 公开地区页面 TypeScript 迁移

本批迁移六个页面和六个组件，并将省份数据、指南展示、地区目录及公开资料请求接到真实类型边界。保留现有页面样式、路由、默认示例、来源说明和文书生成契约。

## 产品范围

- 页面：PublicHome、ProvinceGuide、RegionalGuide、RegionalDocument、RegionalCollection、Home，均使用真实 `script setup lang="ts"`。
- 组件：ProvinceCard、PublicHeader、BrandMark、ServiceIllustration、RegionalRollout、RegionalVerification。静态插图没有运行时输入，其模板也参加严格检查。
- 数据：provinces.ts、regionalGuidePresentation.ts；目录状态：useRegionDirectory.ts。三者保留同名 JavaScript 兼容入口。
- 请求：public.ts 通过统一的 readJSON 传输边界读取地区目录、已收录地区、全国进度、省级历史办事说明、公开报告和版本记录。网络 JSON 从 unknown 开始验证，不把返回值直接断言为业务对象。

导出 ProvinceDefinition、DocumentFieldDefinition、FormLimits、ApplicationExample、EvidenceExample，保留原字段及函数名称。省份、附加字段和文书容量与现有配置逐项一致；未知省份继续返回 undefined，不套用其他省份。

## 行为边界

- 当前地区原件下载带来源 ID 和来源版本；来源未核验时不构造确定的原件地址，版本更新由现有后端返回冲突后重新核对。
- 原有合同 ID 生成流程继续隔离地区、来源、版本、模板和文书类型。江苏、浙江、湖南、肥东专用组件继续保留自己的字段及校验。
- 切换省市立即清除旧目录，取消旧请求；迟到目录、进度刷新结果和上一省份的历史说明不会覆盖当前内容。省级说明保留原来的 15 秒请求时限及离线快照。
- 公开问题报告的显示数据有明确类型；导出保留接口完整原始 JSON，不静默删除未展示的公开字段。
- 品牌资源继续使用应用 BASE_URL；首页搜索、移动导航开关、跳到正文链接和原有页面样式保持。

## 测试证据

先运行原有指南展示、历史字段、地区合同页面和路由测试，基线全部通过。新的测试先失败于缺少真实 TypeScript 模块；挂载测试另复现了进度刷新后的迟到响应覆盖，以及当地原件下载未携带来源版本，分别保留实际 RED 记录后修复。

`node scripts/test-public-page-types.mjs` 通过：

- 12 个组件的严格 TypeScript 和严格 Vue 模板检查，包括 noUncheckedIndexedAccess、exactOptionalPropertyTypes 和 verbatimModuleSyntax。
- 五个真实编译反例拒绝错误的省份、字段容量、表单限制、目录选择和地区请求类型。
- 实际挂载品牌、公开导航、首页搜索、省级历史说明、地区指南及全国进度；目录组合函数实际挂载并验证取消、立即清空和迟到响应隔离。
- 统一请求客户端的地区绑定、取消信号和完整原始报告导出。
- 全部保留的地区指南与省级说明通过展示边界；现有省份及文书配置同值。
- 产品 TypeScript 与组件脚本不含 any 注解、ts-ignore 或 ts-nocheck。

原有回归继续通过：指南原文别名与材料说明、历史浙江字段、14 项地区合同页面集成和 11 项真实 Vue Router 守卫案例。

完整后端回归暴露了旧导出工具的兼容问题：export_document_examples.mjs 通过静态执行 provinces.js 源码读取默认值，遇到新的兼容 re-export 后报 SyntaxError。保留实际 RED 记录后，仅将该工具改为真实导入兼容 API，保留原地区筛选、字段映射、JSON 格式和私有输出位置。工具重新导出 21 个原有地区，backend.tests.test_document_field_regressions 的 7 项测试全部通过；未修改后端测试来绕过问题。

## 验收范围

挂载测试使用 Vue 自定义渲染器、实际组件和受控异步客户端；没有执行实际浏览器排版、原生手机安装或 APK 发布。本批仅交付精确白名单中的前端代码、测试和安全报告，真实浏览器、完整构建及 Android 打包由集成人执行。未修改官方来源、模板、共享契约、后端、数据库、配置、服务或 Git；未启动或调用模型。
