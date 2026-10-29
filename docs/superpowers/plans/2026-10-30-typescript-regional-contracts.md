# 区县文书共享契约与TypeScript渐进迁移

用户已同意保留Python后端、前端逐步TypeScript、共享接口与字段、小程序接区县文书。此次实施此范围，不重新访谈，不重写旧业务。

架构：后端从已核验adapter的实际填写槽构建v1 form-contract，绑定省市区/source/version/template/kind/mode，字段容量取真实技术校验而非假造官方要求。新客户端提交contract_id并再次服务端校验；未带id的旧调用兼容。新共享TS包提供wire类型、运行时校验、空/虚构表单及payload；编译CommonJS给小程序，网页直接复用同源TS。旧JS入口兼容重导出，新TS严格检查，不用any或nocheck假迁移。Android/desktop继续复用网页。

1. 先失败测试：source/version错配、无本区模板、extra空键/稀疏数组/XML/Unicode/日期/容量、不同adapter字段真实差异；不把宽泛ApplicationRequest的全部字段当本区实际槽。
2. 后端新增form-contract与opt-in生成契约，原件下载新可选source/version绑定和response来源headers，旧省级及未带id流程保持；全临时测试库，不改指南/案件数据。
3. 共享TS runtime及声明严格编译，单一CJS产物生成到mini，build --check防漂移，类型错误反例必须真的报错。typed API负责fetch/AbortController/own source context验证。
4. 迁移useRegionalGuide、两个own字段helper/组件/drafts至TS，保留JS兼容入口；网页新契约按钮流程保留默认虚构示例/确认取消/一证据起步，异步切区不继承旧数据。
5. 小程序新增地区选择/本地指南/材料/动态contract填写/原件与生成下载，旧省级入口保留且清晰区分；草稿按scope/source/version/template/kind隔离，迟到请求/弹窗/写文件回调都不得串区。
6. 编译/类型/纯运行时/实际后端全adapter契约与生成、旧测试回归；真实Chrome375/768/1440八份本区文书下载；小程序Page harness与可用官方开发工具验证，不把harness冒充真机。
7. 当前主202/185、history210、outbox377、4294任务及6项用户dirty保护不改；仅授权项目重启、无WindowsOllama或推理、无新采集/夜间自动化、不替用户提交。按共享契约/TS迁移/mini接入/验收文档精确批次Git，禁add .和助手归因。
