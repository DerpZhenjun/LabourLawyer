# 浙江D自身字段组件

新增ZhejiangOwnFields.vue和zhejiangOwnFields.js，沿用现有ll样式、HunanApplicationFields的工程结构与响应式间距。本次只创建独立组件、数据工具、测试与本报告目录；根集成RegionalDocument。

组件props为modelValue、kind（application或evidence）；emit update:modelValue与validation。未传modelValue时载入全虚构默认，支持显式载入虚构示例、清空。暴露validate()返回{valid,errors}，getPayload()验证后返回保留全部字符的深副本；失败抛出的Error.fieldErrors包含字段路径、中文label和message。

```vue
<ZhejiangOwnFields ref="ownFields" v-model="draft" :kind="kind" @validation="validation = $event" />
```

```js
import ZhejiangOwnFields from '@/components/ZhejiangOwnFields.vue'
import {createZhejiangOwnExample, validateZhejiangOwn, zhejiangOwnPayload} from '@/data/zhejiangOwnFields'

const draft = ref(createZhejiangOwnExample('application'))
// 切换文书类型时，由父页面明确初始化对应草稿；组件不会偷偷过滤旧草稿。
function chooseKind(next) {
  kind.value = next
  draft.value = createZhejiangOwnExample(next)
}
// 生成前使用ownFields.value.getPayload()，或：
const result = validateZhejiangOwn(draft.value, kind.value)
const payload = zhejiangOwnPayload(draft.value, kind.value)
```

应用字段恰为provider的23键，独立证据为5个顶层键、每行name/pageCount/source/purpose四键。DATA_FIELDS和LIMITS实际导入backend/regional_zhejiang_oct29d.py校验后，与前端导出契约逐项比较：普通文字300、事实12000、请求最多4项且每项1200、证据最多40项，name/source/pageCount各300、purpose1200。Unicode按Python字符计数，拒绝XML非法控制字符与孤立代理码。copyCount接受空值或1至30的ASCII整数，不自动预填日期或份数。

虚构申请默认包含姓名、公司、事实及具体请求；身份证、电话、出生日期、申请日期、份数和户口类型留空。原件重复“外省非农业户口”，不推测重复项或创造“外省农业户口”；只提供能唯一匹配的明确选项，同时提示不确定时留空后纸面确认。签字没有可自动填写的字段。独立证据从一项起，证据与请求增删始终至少留一行，达到40或4项禁用添加。

未知键即使值为空、隐藏不可枚举键、列表附加键均报错并阻止payload；编辑过程继续保留原草稿未知键，不能通过数组复制或输入事件悄悄丢弃。合法文字、首尾空白、换行、空请求行、数值份数均保持。部分payload的字段可省略，验证与后端实际规则一致。

使用frontend-ui-engineering、ui-ux-pro-max及可访问性清单；本地UX检索确认可见label、关联行内错误、保留输入的模式。控件采用useId关联label、aria-invalid/aria-describedby，错误同时有文字说明，44px控件、可见键盘焦点，600px以下单列。无maxlength裁剪；原有200字保留，超长文字继续显示并指明调整处。

先运行API不存在的真实RED，随后实现GREEN。额外实测发现稀疏证据数组会被forEach跳过，新增RED复现后改为逐索引检查；避免JSON序列化为null后才被后端拒绝。最终test-zhejiang-own-fields.mjs共16检查通过，包含实际provider契约/有效性parity、Vue SFC脚本/模板/scoped样式编译、Vue内存renderer真实挂载、v-model输入/增删、字段label关联、200字输入、301字和1201字错误关联、4/40上限、未知草稿键不丢弃。Vite170模块构建2.14秒通过。

真实浏览器整页验收尚未执行，留待根集成后完成。本任务没有启动服务、Word或模型，没有修改RegionalDocument、共享路由、DB或Git。另按根授权补充D江苏既有9项中的发布生命周期再适配断言，3.371秒通过；D江苏provider无修改，其56文件白名单仅刷新测试/日志等实际SHA。
