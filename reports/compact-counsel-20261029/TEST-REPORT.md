# 客服数字人小窗改版

日期：2026-10-29，Asia/Shanghai。范围：现有Vue数字人容器与Next.js数字人页面；没有改动当地指南、官方模板、生成路由或数据库。

## 界面约定

- 右下角非模态小窗：桌面400px宽，高最多640px，随可用视口收缩；手机左右各留12px。
- 上方人物区域最多128px，固定上半身镜头，不可拖拽缩放成全身；其余空间用于咨询。
- 独立访问数字人服务时也使用400×680px以内的卡片。
- 收起使用隐藏而非销毁iframe，重新展开保留对话；关闭可退出。背景可以滚动、搜索与填写；没有遮罩或全屏按钮。
- 操作按钮至少44px、明确中文标签、可见焦点；Esc关闭并还原焦点。跨iframe关闭消息同时核对来源地址和窗口。

## 真实验证

先运行新回归检查，在旧页面复现失败：`Digital counsel must not fill the desktop width`。修改后使用已运行的5173/3000/8000服务，不新建验收后端，不访问真实案件。

`node scripts/verify-compact-counsel.mjs --answers`：10项通过。

1. 独立页面紧凑卡片，形象完成加载。
2. 虚构测试问题经Ubuntu `qwen3.8:27b`完整返回“客服小窗测试成功。”。
3. 375、768、1440px卡片无横向溢出，输入框可见（3项）。
4. 小窗打开时实际操作背景省份搜索框，无遮罩、inert或页面滚动锁。
5. 收起后恢复同一iframe，不重建对话。
6. 375、768、1440px浮窗尺寸与页面无溢出（3项）。

另外验证Esc关闭、焦点回到入口，两页控制台均无错误或警告。README截图是已完成真实问答的400×680px卡片，不使用整页场景截图。

- `npm run build --prefix frontend`：158模块构建通过。
- `npm exec --prefix ChatVRM -- tsc --noEmit --project ChatVRM/tsconfig.json`：通过。
- `npm test --prefix desktop`：3项通过。
- `npm run sync --prefix mobile`、Gradle离线`assembleDebug`：通过；APK签名校验通过，沿用原调试证书，USB覆盖安装返回Success，安装后versionCode为3、versionName为1.1.0-preview.2。
- `npm run dist --prefix desktop`：安装版和便携版构建通过，按版本存储，新包保留生产依赖许可通知；安装程序本轮未执行安装。

本机原始证据位于被忽略的`.runtime/compact-counsel-20261029/`，含RED记录、MCP结果和6张响应式截图。没有绕过此前手机模拟点击/调试诊断限制；手机原生交互不计入本轮网页MCP通过数量。软件包仍为需单独运行后端和数字人服务的客户端预览，未启动Windows模型。
