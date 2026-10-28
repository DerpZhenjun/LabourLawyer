# 滨海 响水离线文书验收

本轮使用两个区县各自独立正式来源和自身canonical空白申请书、证据清单；未重新采集、不写公开DB、不启动站点/服务/模型、不使用Git，也没有调用远程Ollama。全部身份、号码、地址、单位、事实及请求为虚构测试数据。只验证离线模板填写，不表示候选网页或提交能力通过。

## 实际渲染和逐页查看

原件7张（空白申请书6页，证据表1页）全部实际渲染并以view_image original打开。两县相同完整SHA才共享参考渲染，4个自身原件SHA分别核验。初轮4文件共6张也全部打开，发现正常出生日期的月份/日跨到下一行；原始失败文件及图片保留在本目录根和render/，不作为合格交付。

经主代理明确授权，仅在JiangSuSheng专用分支使用紧凑ISO生日格式，复用原14pt、方正仿宋_GBK、下划线及其他run属性，不缩字体或改变原件。回归先真实RED，后GREEN。修复后birth-date-fixed/4文件重新实际导出与渲染，共6张：

| 文件 | 页数 | 实际查看结果 |
|---|---|---|
| 320922-application.docx | 2 | 第一页生日同一行，完整填写本人和唯一单位、请求和事实、此致、签字和日期留空；第二页附件份数3/2和五条注释完整。无裁切、重叠或空白尾页。 |
| 320922-evidence.docx | 1 | 自身委员会标题，证据首项编号1，六列与3页数字正确；提交/接收签字及日期留空，无幽灵额外证据。 |
| 320921-application.docx | 2 | 同上，以响水自身名称填写，生日换行已消失。完整双页均查看。 |
| 320921-evidence.docx | 1 | 同上，以响水自身名称填写，完整一页已查看。 |

共19张页面图实际打开：7张原件参考 + 6张初轮失败检查 + 6张修复后完整复验。最终每页PNG路径与DOCX完整SHA在birth-date-fixed/render-manifest.json，不以首屏或XML抽检代替逐页检查。

## 原件和包保真

原件申请书SHA `99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3`、证据SHA `c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c` 前后不变。最终4件ZIP清单保持，每件仅word/document.xml改变，其他每个包部件逐字节一致；关系、样式、主题、字体和设置均未重建。单section及原A4/边距不变。详见birth-date-fixed/package-checks.json与新增专项测试。

## 渲染方式与剩余限制

本轮真实运行打包render_docx.py，因soffice.exe不存在失败，日志packaged-render-probe.log保留。实际方式是独立隐藏Word只读ExportAsFixedFormat + workspace loader所列bundled Poppler，未使用用户LibreOffice或附着已有Word。导出前无既有WINWORD，否则脚本直接中止；生成后与浙江协调串行导出，未并发。独立Word对象已Quit。

生日槽修复后的8项目标测试通过；江苏整个专项最终结果见jiangsu-tests.txt。不跑全量测试。最终仅离线文书验收通过，保持未发布，product web QA仍NOT_RUN，未验证在线登录或业务提交。未对长事实、多证据或其他主体表开展新视觉压力验收，不把本轮结果扩大成这些场景的保证。
