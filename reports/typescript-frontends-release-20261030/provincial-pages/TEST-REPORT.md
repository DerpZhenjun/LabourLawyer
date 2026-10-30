# 省级历史文书页面 TypeScript 迁移

完成浙江申请书、浙江证据清单及广东两个既有路由包装页，另迁移 GenerateConfirmation、HunanApplicationFields、FeidongApplicationFields 三个组件。湖南和肥东字段函数移至同名 TypeScript 文件，原 JavaScript 文件仅转导出以保留旧导入路径。

请求边界 frontend/src/api/provincial.ts 使用统一 apiURL，保留 Axios Blob 响应模式及 30 秒超时，运行时确认返回值确为 Blob；未知错误只展示明确的文字 detail 或中文回退提示。纯省级校验结果与错误类型放在 packages/regional-contracts/src/provincial.ts，没有修改区域共享 index 或既有小程序生成绑定。

原官方字段、字符容量、折行宽度、Unicode 行为、示例和日期/份数默认值保留。省份未找到时明确拒绝挂载，没有借用其他省份。合法的旧 JSON 扩展键仍保留；非法 JSON 或错误列表结构保留原始本机存储，提示清除后重填，并防止保存/卸载覆盖。存储本身不可用时仍可生成。湖南空列表附带的旧扩展属性在编辑时保留，由原校验拒绝；不静默裁剪输入。

测试先观察到 SFC 未启用 TypeScript 的失败，再完成迁移。新增存储不可用、非 Blob 响应、空旧列表元数据保留的测试也分别观察到失败后修复。

验证命令：

```
node scripts/test-provincial-page-types.mjs
node scripts/test-hunan-fields.mjs
node scripts/test-feidong-fields.mjs
node scripts/test-document-clients.cjs
node scripts/test-regional-form-integration.mjs
```

结果：

- 七个所属 SFC 及所属 API/数据文件通过严格 Vue TypeScript 检查，包括 strictTemplates、noUncheckedIndexedAccess 和 exactOptionalPropertyTypes。临时配置继承项目约束，没有关闭检查。
- 两个负向类型夹具确认数字请求项和数字当事人行无法赋给对应类型；没有使用类型检查抑制指令。
- 实际挂载迁移前版本 78903a98 和新 TypeScript SFC，逐项对照 21 份申请书、13 份证据清单的 URL、完整请求和下载选项，共 34 组一致；取消确认不发送请求，空白模板载荷为独立空对象。
- 迁移前请求仅保存 SHA 固定夹具，见 BASELINE-PAYLOADS.json；普通重跑不依赖私有原 SFC，干净检出也会检查实际挂载页面的 34 份请求是否匹配。重录必须显式指定 --record-baseline 并提供原始 SFC。
- 湖南 17 项函数、实际离线提供器容量对照、Vue 挂载、字段标签与错误关联、列表增删、原文和旧元数据保留检查通过。
- 肥东原有空白/示例、控制字符、精确容量、Python Unicode 宽度/折行对照、SFC 编译检查通过；新增真实编译模板的输入事件挂载验证超容量保留、错误状态和事实原文。
- 实际挂载两种省级页面，非法草稿在保存及卸载后原字符串仍相同；证据草稿未知头字段继续保留。存储失败不成为额外生成门槛，非文件响应明确拒绝。
- 原小程序 34 份请求回归通过；区域表单原有 14 项挂载、取消及合约绑定集成回归通过。

所有页面测试使用内存 Vue 挂载及合成网络/下载边界，没有调用模型或真实生成服务，没有数据库、服务、设备或发布操作。本报告不声称浏览器、Android 或真机验收；这些由集成发布任务负责。配置、原始模板、官方来源、现有小程序绑定和冻结报告均未修改。
