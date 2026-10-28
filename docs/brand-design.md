# LabourLawyer 品牌标识

标识以文书、对话和双 L 为共同语言。主标识是折角文书中的双 L，AI 助手保留双 L，外轮廓换成带尾部的对话框。所有图形为本项目原生 SVG 路径，不依赖字体、图标库、外部图片、滤镜或动画。标识不暗示政府机关、司法机关认证或律师身份。

## 设计约定

- 保持既有主色 `--ll-primary: #17675e`；白色主体与主色形成清晰对比，折角辅色 `#acd5c7` 仅用于主标识局部层次，不承担状态含义。
- 32×32 坐标系、8 单位外圆角、2.2 单位内线宽；24px 时内线仍约1.65px，32px 时约2.2px，48px 时约3.3px。无细小文字或国徽、政府印章。
- 主标识和助手图形的双 L 使用相同线端和拐角，不将字体图标作为新 logo。页头仍保留 LabourLawyer 和中文说明，标识不独自承担理解产品名称的任务。
- 标识最低建议24px；favicon可由浏览器缩放到16px，此时保留文书整体轮廓，不能依赖辨认双 L。交互按钮的可点区域至少44px，图形尺寸不等于点击区域尺寸。

## 资源

| 文件 | 用途 |
|---|---|
| `frontend/public/brand/labourlawyer-mark.svg` | 主标识 |
| `frontend/public/brand/counsel-mark.svg` | AI 助手入口及对话语境 |
| `frontend/public/favicon.svg` | 与主标识同一几何与颜色的浏览器标识 |
| `frontend/src/components/BrandMark.vue` | 页面内统一使用的组件 |

## 组件 API

```vue
<BrandMark />
<BrandMark :size="24" variant="assistant" />
<BrandMark :size="48" label="LabourLawyer" />
```

`variant` 为 `brand`（默认）或 `assistant`；`size` 为正数像素值，默认32；`label` 默认空字符串。默认图形用于有可见文字或已有按钮名称的场合，使用空alt并从无障碍树隐藏，避免重复朗读。独立有意义图片请传label；交互入口的按钮/链接仍应有自己的清楚名称，组件本身不添加交互或tabindex。宽高属性与同值的动态尺寸样式共同保留空间，避免延迟加载造成偏移。静态资源路径跟随Vite BASE_URL。

页头示例将图形作为装饰、链接命名为“LabourLawyer 首页”，可见文字保持不变；移动页头保留32px图形和至少44px链接高度。

## 技能搜索依据

本轮真实运行 ui-ux-pro-max 的 `search.py`：

1. `legal document service minimal trustworthy --design-system -p LabourLawyer`：返回Accessible & Ethical，适用高对比、清楚焦点、44px目标和语义。建议蓝金配色与本项目既有teal不一致，因此保留项目颜色；营销转化、轮播及销售CTA与本次标识任务无关，未采纳。
2. `decorative icon accessible name --domain icons -n 3`：首条为icon-context-accessibility，采用“可见文字旁装饰图隐藏，有意义图提供文本替代”；未采纳其图标库推荐来替代原创标识。
3. `accessible reusable component props --stack vue -n 3`：采用显式只读props和以输入/呈现结果为主的组件验证方式。

同时按frontend-ui-engineering及其canonical无障碍清单保留可见焦点、语义链接、尺寸预留及小屏空间。没有引入新字体、依赖或服务。

## 验证记录

本轮将实际`BrandMark.vue`和`PublicHeader.vue`通过项目现有Vue编译器/esbuild编译为本地自包含HTML，以Chrome原生`file://`打开；没有启动Vite、HTTP站点或其他服务。agent-browser使用独立会话`nationwide-js-brand-20261028`，已关闭。不是手工重画的假页头。

- 主标识与助手图形各自24/32/48px，在白底和深底共12个样本实际加载、截图并以view_image original查看。24px仍能分开两条L，折角/对话尾部不混淆；32px为默认主尺寸，48px轮廓和线宽连续。白色与teal对比度按sRGB相对亮度计算为6.69:1；favicon与主标识SVG字节一致。
- 页头实际查看320/768/1024/1440px四种视口，documentElement.scrollWidth分别等于对应视口宽度，无横向溢出；320px品牌链接约162×50px、菜单按钮62×44px，二者不碰撞。小屏菜单真实点击展开/收起，aria-expanded由false变true再恢复。
- 页头品牌链接和导航真实Tab/Shift+Tab聚焦，读取到3px可见焦点线，并截图查看；品牌链接名称为“LabourLawyer 首页”，旁有文字的图形为空alt/aria-hidden。独立展示样本有LabourLawyer/AI助手替代文本，14个img均complete且naturalWidth>0。运行时错误列表为空。
- 本地验收文件位于`.runtime/brand-qa-20261028/`：`build-preview.mjs`、`preview.html`、`320.png`、`320-menu.png`、`768.png`、`1024.png`、`1440.png`和`brand-focus.png`。这些是本地检查证据，不作为公开品牌资源，不加入应用路由。

未声称运行全站构建、axe或真实屏幕阅读器验收；主代理另行整合AI浮钮和QA页。此静态预览不等于候选指南站点验收。
