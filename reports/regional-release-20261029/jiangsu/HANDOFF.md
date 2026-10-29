# 东台 射阳自身模板本轮适配

本轮实际推进东台市320981、射阳县320924各自申请书和证据清单的严格离线填写及公开来源摘要。此前已有独立原件和布局适配结构，本轮未重采原件；增加了调用者不能指定路径、原件实际SHA须相符的可执行候选入口。尚未发布，未写主DB，候选网页验收NOT_RUN，在线登录/提交未验证。

## 实际官方复核

东台来源 `https://ycdt.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=100&iddept_ql_inf=11320981014396886W4002014302002&ql_kind=20&iddept_yw_inf=11320981014396886W400201430200201`，机关“盐城市东台市人力资源和社会保障局”，source_id `5e53e6d3179046433e5fdcb8`。

射阳来源 `https://ycsy.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=98&iddept_ql_inf=11320924737070337G4002014302002&ql_kind=20&iddept_yw_inf=11320924737070337G400201430200201`，机关“射阳县人力资源和社会保障局”，source_id `69952614ad2cf51d91ee7460`。

独立agent-browser会话regional-release-js-20261029真实访问并原生打开各4个材料详情。地区、机关、任务、全部已解析字段、8个材料附件ID及URL均与10-28自身记录一致；16个自身canonical原件SHA无差异。两地公示法定/承诺均45个工作日、到场3次、纸质材料2/2/1/4，保留自身地址/电话；东台投诉123333仍原文未纠正。具体摘要与复核时间见source-recheck.json；公开截图是各code下official-recheck.png、materials-rechecked.png，原始HTML不放入公开白名单。选择关闭材料弹窗的快照结构变化曾使本地regex失败，doctor7PASS后使用实际观察到的panel-tool-close原生控件恢复，不代表政府故障。

## 可执行接口和共享接入点

新增 `backend/regional_jiangsu_candidates.py`：

- `SUPPORTED = {'320981','320924'}`，只限本批自身两地。
- `candidate_contract(guide)`：两份真正空白的元数据和实际canonical SHA核验，显式published=false/generation_enabled=false/web_qa_status=NOT_RUN；原件缺失或SHA改变即ValueError，不以缺私有原始捕获为理由造可生成状态。
- `fill_candidate_document(guide, kind, data)`：kind仅application/evidence；精确自身地区、source URL/digest、agency/task、annex、SHA、download身份和canonical目录，拒绝任意传路径、异区/异城、样例、标题占位及重复同类附件，返回PreservedPackageDocument。它直接调用fill_blank_document，不会再次进入dispatcher/router，无DB/网络/模型/服务副作用。

主代理拥有共享文件，本子任务未修改。建议接入：`backend/routes/regional_guides.py`现有`/generate`的`elif adapter==BLANK_ADAPTER`分支，对`g['region_code'] in SUPPORTED`调用`fill_candidate_document(g,payload.kind,data.model_dump())`，其他仍原函数。沿用现有BlankApplicationRequest、EvidenceRequest、blank mode、source_id/version检查、文件响应头，不另增adapter常量或绕过select_template。`backend/regional_adapters.py:with_reference_capabilities/checked_reference_adapter`已有两地精确blank_binding，可沿用；若要在能力展示阶段也抵御缺失原件，对这两地先candidate_contract，失败时清空其can_generate/document_types，不能把离线合同false当作主站发布许可。

请主代理用真实router和**独立临时RegionalStore/ASGI**验证两地各2件HTTP输出、错误source/version/template及缺失原件409，不启动候选HTTP服务器或改主DB。本子任务只证明函数/内存文档和版式，未冒称ASGI/主站已经调用新入口。

## 公开来源和封存边界

每地新`public-guide.json`含完整公开结构字段/栏目/材料及8附件身份，`public-provenance.json`包含自身source/agency/task、复核时间、公开截图、每个canonical原件下载URL与完整SHA。去掉raw捕获引用和响应headers，不公开HTML、SSO会话、cookies或认证资料；指南本身仍candidate、模板can_generate=false。两份结构摘要和必需canonical文件可作为主代理独立ASGI库的输入，不依赖封存raw目录。

新增测试将自身公共空白复制到全新临时根目录（只有templates，根本没有reports/raw/DB），实际合同和生成通过；删除自己的原件后明确阻断。运行时原件必须随公开发行包提供，缺失/被替换即不能宣称支持。公开摘要不能替代未来候选网页验收，也不声称全国或江苏全省模板统一。

## 真实版式与数据保真

最终`render-no-links/`下4份文书共6张：东台申请2页/证据1页，射阳申请2页/证据1页，全部view_image original逐页打开。姓名/单位/号码/住址/事实全为虚构；ISO生日同一行，3/2份数独立；签名、指模、盖章、日期空白。每份证据从1项开始，编号1、来源/目的/复印件/3页六列对应，无多余虚构证据。无裁切、重叠、缺字、破表或空白尾页，申请书5条注释保留，另一主体表不混入输出。当前仅这一合成输入的视觉范围，不覆盖未测试长事实或多项证据压力场景。

申请书原件SHA `99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3`，证据原件SHA `c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c`，逐地前后不变；每件只修改word/document.xml，申请书20个其他ZIP部件/证据11个其他部件逐字节保持。完整source/output SHA见package-checks.json，最终PNG路径见render-manifest.json，审批仅绑定本批输出SHA。

## Word隔离的真实经过

旧脚本因已有用户110792中止，render.log保留。首个新空90552在PID函数返回uint的PowerShell绑定异常处失败；第二空90680因错误使用Application.Hwnd（Word句柄实际属于Window）被安全守卫拦下，二者都0文档。获得清理授权后先核对唯一新增PID、可执行文件、创建时间、不可见窗口和0文档记录，精确清理自身空实例，无宽泛Stop WINWORD。

改为CoCreateInstanceEx后先成功93620导出4件并仅Quit自身；主代理追加禁链接要求时已启动该次，随后另保留成功证据并再执行显式禁链接最终26372批次。最终4个Document.Window.Hwnd均映射26372；宏3、UpdateLinksAtOpen=false、只读/不保存，恢复自身选项后仅Quit26372，before/after原110792均在，未接管或停止它。Word隔离证据、两次失败日志及清理记录均保留，不只展示通过日志。此处修正本地保守守卫，未绕过任何候选服务策略拒绝。参考Word官方Window.Hwnd定义：https://learn.microsoft.com/en-us/office/vba/api/word.window.hwnd。

测试先4方法实际RED，再GREEN；最终目标测试结果见targeted-tests.txt。未跑全量，未Git提交，未改共享dispatcher/routes/config、README或ModelFinetune，未启动Windows模型或任何候选/替代服务。公开文件逐项SHA白名单见public-file-allowlist.json。

主代理后续已报告：共享/generate的两地BLANK分支接入上述无path入口，新test_jiangsu_candidate_dispatch.py真实RED0calls→GREEN4calls，四虚构POST200、四错误地区source409，测试输入使用本批public-guide.json。本子任务未自行重跑这份ASGI测试；其主代理证据和全量结果另存主交接。本批最终提交白名单已收窄为代码、公开结构来源/截图、审批摘要及4个必需自身空白原件；虚构生成DOCX、原始browser-actions/HTML和Word运行/进程日志仅本地保留，不列入提交候选。中间故障证据未删除。
