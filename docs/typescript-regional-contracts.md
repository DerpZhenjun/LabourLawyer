# TypeScript 与区县文书共享契约

迁移采用分批实施：保留 Vue 页面、Python 文书适配器及历史省级入口。Android 和桌面继续复用网页；没有重打包已经发布的预览安装包。

## 字段如何保持一致

后端从已核验适配器的实际填写槽生成 `GET /api/regional-guides/form-contract`。查询必须带省、市、区县、来源 ID、版本、模板 ID 和文书种类。表单描述声明字段、选项、容量、空白结构及既有版式限制；容量是软件填写限制，不冒充官方材料要求。

`packages/regional-contracts/src/index.ts` 提供共享类型、运行时验证、空白与虚构示例、生成请求构建。网页直接使用 TypeScript；`scripts/build-regional-contracts.mjs` 编译同一份源码为微信可加载的 CommonJS，`--check` 检查漂移。小程序没有另一套区县字段规则。

提交带 `contract_id`；服务端重新匹配当前地区和模板、重新计算契约后验证。来源或契约过期返回 409，非法字段或容量返回 422。返回的 Word 同时核对来源、版本、文书来源类型和契约 ID。历史未带契约 ID 的调用保持兼容。

## 已迁移范围

- 地区 API 客户端及 `useRegionalGuide`、`useRegionalForm`。
- 江苏、浙江自身模板的字段模型、草稿组合函数和两个 Vue 字段组件。
- 通用区县表单渲染器；原有湖南和肥东专用版式组件保留。
- 后续批次将区县页面、群众入口、管理页面与历史省级表单的脚本一起迁入 TypeScript。现有 34 个 Vue 文件均以严格类型与模板检查覆盖；旧模块保留兼容入口。

选定 TypeScript 和 Vue 组件启用严格类型、严格模板及索引检查；兼容 JavaScript 入口与静态 JSON 保留，未用关闭严格检查代替页面迁移。错误类型反例须实际被编译器拒绝，不用 `any` 或忽略注解代替迁移。

## 小程序开发

导入 `miniprogram`，在省份页面进入“按市、区县填写当地文书”，选择办理地区，核对来源后填写并确认生成 Word。未核验地区不会借用省级或邻区模板。历史省级表单保留独立入口。

从源码更新后先运行：

```powershell
npm --prefix frontend ci
node scripts/build-regional-contracts.mjs
node miniprogram/scripts/sync-data.cjs
```

微信运行时不支持直接把 JSON 当作 `require` 模块。三份已有配置由同步脚本生成 JS 模块，原始 JSON 仍为唯一数据来源。开发工具“服务端口”仅用于本地自动化验收；无需为填写文书启动模型，也不会自动上传、发布或代交仲裁申请。

## 验证

```powershell
npm --prefix frontend run build
node scripts/build-regional-contracts.mjs --check
node scripts/test-regional-contracts.mjs
node scripts/test-regional-contract-parity.mjs --fresh-source-contracts
node scripts/test-regional-api.mjs
node scripts/test-own-field-types.mjs
node scripts/test-regional-form-integration.mjs
node scripts/test-regional-document-routing.mjs
npm --prefix miniprogram test
python -m unittest backend.tests.test_regional_form_contracts -v
```

契约校验使用虚构内容和独立临时数据库。实际测试范围、真实网页下载及模拟器限制见 [本轮验收](../reports/typescript-regional-contracts-20261030/TEST-REPORT.md)。区县覆盖数量仍为 202 份指南、185 地开放填写生成，本轮没有新增或修改官方来源。

后续页面迁移与 Android 1.2.0-preview.1 的实际结果见 [发布验收](../reports/typescript-frontends-release-20261030/TEST-REPORT.md)。网页、Android 共用构建；AI 请求/远程状态由 `packages/client-contracts` 同源生成供微信与数字人代理使用。直接运行 TypeScript 测试，本轮使用 Node 24.19.0。

小程序全部 7 页、应用入口及两个业务工具现使用 TypeScript；网页剩余旧业务辅助模块也已迁移。运行 `npm --prefix miniprogram run compile` 后提交 `.ts` 与生成 `.js`，`npm --prefix miniprogram test` 会检查严格类型、生成漂移及 34 类请求与迁移前的 SHA 一致性。省级目录、字段定义与容量 DTO 来自 `packages/client-contracts/src/documents.ts`，本地显示简称与服务端目录字段分开处理。更新的 [小程序开发说明](../miniprogram/README.md) 和 [本轮验收](../reports/miniprogram-typescript-20261030/TEST-REPORT.md) 说明了真实模拟器范围和无需重复打包相同 APK 的依据。
