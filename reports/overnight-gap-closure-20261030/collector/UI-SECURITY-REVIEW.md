# 管理员采集界面独立检查

静态检查了实际 `OfficialCollector.vue`、`useOfficialCollector.ts`、共享 collector parser、认证会话/路由、后端 router 和证据响应；另运行 `node scripts/test-official-collector.mjs`，结果通过。未发现本轮新增的可操作安全缺陷。

- 管理页面有管理员路由检查；后端每个队列/证据端点独立要求管理员，不依赖前端隐藏按钮。身份变化时根组件按用户 ID 重新挂载；卸载清空页面状态并取消请求，下载落盘前再次核对身份。
- 来源 URL 经过协议/官方域名检查，外链使用 `noopener noreferrer`；页面标题、错误和地区以 Vue 文字插值呈现，没有原始 HTML 渲染。后端白名单输出与前端白名单 parser 都丢弃进程路径、原始异常、Cookie 和原始 HTML。
- 证据以 Bearer 认证请求获取，核对字节数及 SHA256 后再保存；不会将 token 拼进图片 URL。HTML 和越界文件名不在证据接口白名单。
- `guide_observed`、文件下载和队列结束都没有被显示成官方核验或已支持地区。重试上限为两次，没有全国队列或自动模型请求。

本次是代码与响应契约检查；新 bundle 的真实 8088 页面、401/403、登录退出和证据下载交互仍由主任务上线前独立验收。已知的传输后大小检查与磁盘留存限制见 `REPORT.md`；本检查没有更改冻结运行时、API 或存活 worker。
