# 地区文书表单契约接入验收

本交付让地区文书页先取得当前来源、版本、模板、文书类型和适配器绑定的表单契约，再展示栏目和请求生成。生成通过地区 API 客户端携带 `contract_id`。合同读取失败时只显示错误和重试入口。

## 实现

- `useRegionalForm.ts` 管理合同加载、完整上下文及合同 ID 隔离的草稿、确认快照、取消信号和下载状态。来源、版本、模板、类型、地区或模板身份变化会立即清除旧合同和确认。旧确认函数、迟到响应和已经开始保存的结果不能在新范围显示成功。
- `RegionalContractFields.vue` 使用严格 TypeScript。通用表单的字段、选择项、日期格式、份数范围、字符容量和列表容量全部来自服务端合同。超长文本、未知键、隐藏键、数组额外属性及稀疏项不会通过编辑被悄悄丢弃。错误关联具体控件，至少保留一项可见列表行。
- `RegionalDocument.vue` 保留 JavaScript 页面编排，新的状态及通用渲染器使用 TypeScript。江苏 E、浙江 D/E、湖南及肥东继续使用自己的专用组件、虚构默认值和校验器，按完整上下文及合同 ID 重建组件。保留清空、虚构示例、取消确认和键盘操作。
- 旧 `/documents/:province/:kind` 带完整单值 `city`、`district` 时，保留全部查询参数和锚点，转到地区文书页。缺失、重复或空的地区参数转回地区核对页；无地区参数保持旧省级入口。此修复避免明确选择相城区时显示旧省级锡山区表单。

## RED 与 GREEN

保留四份实际失败记录：初始缺少合同状态模块、同值上下文属性顺序导致草稿失效、旧确认回调在新区新对话框打开后触发新区生成、旧路径忽略地区参数。修复后重复执行全部相关测试。

- 页面与状态集成：14 项挂载、上下文取消、合同字段和异步下载案例通过。
- 实际 Vue Router 内存历史导航：11 项守卫案例通过。
- 新状态模块及通用 SFC：`strict`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`、`verbatimModuleSyntax`、`strictTemplates` 检查通过。
- 江苏专用组件 22 项、浙江专用组件 20 项、湖南专用组件 16 项，以及肥东的容量、无损载荷、后端一致性和 SFC 编译回归通过。
- 已冻结的上一阶段 25 项精确白名单文件逐项 SHA 校验通过，未修改其代码、测试或报告。

## 验证范围

页面集成测试挂载实际页面、实际合同状态和实际通用渲染器，客户端使用延迟可控的测试实现；专用组件在此测试中使用接口替身，其真实挂载和 provider 一致性由各自原有测试覆盖。测试数据为明确虚构内容，不提交实际申请。

本交付不包含真实浏览器下载、后端重启、文书渲染或发布结论；这些由集成人执行。未修改共享契约、客户端 API、后端、候选配置、数据库、服务或已冻结官方来源；未执行模型、Word 或 Git 操作。

## 复现

在仓库根目录使用现有项目依赖运行：

```text
node scripts/test-regional-form-integration.mjs
node scripts/test-regional-document-routing.mjs
node scripts/test-jiangsu-own-fields.mjs
node scripts/test-zhejiang-own-fields.mjs
node scripts/test-hunan-fields.mjs
node scripts/test-feidong-fields.mjs
```

集成脚本自动生成仅位于私有运行目录的临时类型检查配置。公共交付只包含精确白名单中的代码、测试和安全报告，不包含依赖目录、完整运行诊断或私人草稿。
