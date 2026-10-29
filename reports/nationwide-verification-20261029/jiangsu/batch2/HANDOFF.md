# 江阴 宜兴自身正式指南与离线文书

两地均新增自身候选证据，未发布、未写DB、候选网页NOT_RUN；本子任务不增加181已发布指南/166可生成计数。第一批清江浦/淮安区的31个白名单文件保持原字节，其发现状态不被本批替换。本批只由根线程集成，不自行Git或启动服务。

## 独立来源

江阴市320281：自身门户 https://wxjy.jszwfw.gov.cn/ →个人服务关键词“仲裁”→本事项办事指南，实际新标签到 https://wxjy.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=39&iddept_ql_inf=1132028101404259474002014302002&ql_kind=20&iddept_yw_inf=113202810140425947400201430200201 。source_id `3d304f186983f34c4170a398`，机关“江阴市人力资源和社会保障局”，业务办理项113202810140425947400201430200201。

宜兴市320282：自身门户 https://wxyx.jszwfw.gov.cn/ →个人服务“仲裁”→本事项办事指南，实际到 https://wxyx.jszwfw.gov.cn/jszwfw/publicservice/itemlist/showDetail.do?webId=40&iddept_ql_inf=1132028201404667594002014302002&ql_kind=20&iddept_yw_inf=113202820140466759400201430200201 。source_id由规范URL经regional_guides.digest[:24]计算，见自身guide.json；机关“宜兴市人力资源和社会保障局”，业务办理项113202820140466759400201430200201。

独立Agent Browser `js-oct29-verify`0.38.2真实打开两市12栏目、各4个材料详情和自身流程图，所有10张正式/详情图均实际查看，18个公开附件分别独立HTTP200下载，不通过邻区原件复制。两地8个材料附件和1个流程图均保留自己的GUID/URL/原名/下载UTC时间/字节数/SHA。public guide为结构摘要；临时DOM仅取12个栏目在进程内交既有严格parser，未存HTML、HAR、headers、cookies、登录状态或SSO跳转参数。

江阴窗口原文“江阴市君巫路100号1号楼1楼 ;南侧窗口”；办公时间上午8:30-11:30，下午夏令14:00-17:30、冬令13:30-17:00；咨询0510-86800756，投诉0510-12333。宜兴窗口原文“江苏省宜兴市教育西路1号宜兴市人力资源和社会保障局6号楼403（仲裁科）；7号楼1楼权益服务大厅劳动仲裁窗口”；法定工作日上午8:30-11:30，下午13:30-17:00；咨询0510-87988190，投诉“电话，0510-12333”。各自45个工作日法定/承诺、到场3次与到场说明原文保留，没有推广为全省要求或纠正官网时限。

各4材料：证据材料复印件2份、证据清单原件和复印件2份、申请人或代办人双方身份证明原件1份、申请书原件4份；详情A4等原文见自身materials。身份证明的空白附件实际是仅标题“身份证复印件”的占位，证据材料两附件也是仅标题，不作为生成模板。申请书原件另有副本按被申请人人数提交说明，与材料页4份并存保留，不代替用户决策。两地真正空白申请书SHA99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3，证据清单SHAc40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c；自身下载证明之后才复用既有结构位置。

两张自身仲裁流程PNG也独立下载并实际查看，SHA均dc407a951d748964846c061b0331167db5c0178a8a7515f6ab933494c74aa8ee。图节点包括申请、受理、案前调解、立案审核、组庭审批、排庭/举证/答辩、请求变更/反申请、庭审准备、审理、仲裁确认、归档、结果反馈；导出图和正文分别保留，图无办理方式证明。

## 网上办理的差异

江阴自身在线按钮实际原生点击，等待新标签出现个人/法人登录及验证码后止步，状态auth_required；未输凭据、不答验证码、不提交。仅保存origin/path/界面标志的online-boundary.json及登录空界面截图，没有原始SSO URL。该入口带旧HTTP回跳，但本批没有尝试登录或回跳，不能承诺登录后可提交。

宜兴自身正式页表内写“窗口办理,网上办理,快递申请”，但目录目标行及指南本身都没有在线办理按钮，仅办事咨询。最后实际DOM复核可见在线按钮数0，online-entry-check.json绑定自身精确来源及UTC时间；online_status仍unverified、entry_url空，并保留提示。不能沿用江阴auth_required或推断宜兴不支持网办。

## 固定来源适配入口

`backend/regional_jiangsu_oct29.py`：ADAPTER=`jiangsu_own_blank_oct29_v1`，SUPPORTED只320281/320282。`candidate_contract(guide)`核验4个必需原件；`fill_candidate_document(guide,kind,data)`只接受application/evidence，不接受调用者路径。逐地固定省/市/区、正式URL及digest/source_id、事项名/标题、机关/task、栏目机关/task、自己annex/material_id、blank身份、下载URL、原名、file_type、文件固定相对路径和实际SHA；重复/缺失/损坏/样例/异区均阻断。直接调用字节证明相符的结构布局和PreservedPackageDocument，不递归进入共享dispatcher，无网络/DB/模型/Word副作用。

4个运行必需原件就是各guide.json内application/evidence两个文件，路径固定在 `reports/nationwide-verification-20261029/jiangsu/{code}/originals/{own-annex}/{official-name}.docx`。根线程集成时应随公共fixture一起保留这些原名路径；不能悄悄迁往canonical目录而不同时更新严格合同和测试。共享registry可登记这个独立adapter key并在能力展示/生成都调用严格合同；沿用现有BlankApplicationRequest/EvidenceRequest和source/version/template检查。父线程负责独立RegionalStore/ASGI与真实浏览器，尚未由本子任务验证。

模板meta保留can_generate=false，另记offline_document_type和offline_qa_status；合同和文书视觉通过只证明离线，不授权发布。公共包只需4个真空白DOCX和2个自身流程图；下载的身份证样例JPG、非必需样例和占位原件保留本地，排除提交白名单，避免分发不必要身份证图像。所有下载元数据可公开但不表示被排除原件随包提供。

## 测试和真实视觉范围

新增test_jiangsu_oct29.py：最终7个unittest方法，含多组源/地区/机关/task/附件/类别/SHA/文件路径/缺件/腐败/重复等反例，自身4件正例，clean-only临时根只复制2必需原件也可生成。实际RED为模块未实现，GREEN后视觉又抓出本批代码份数回归：把份数修复和closing循环合并导致在日期处提前break，附件未处理。已分开两循环；份数新测试真实RED(3/3)→GREEN(3/2及未填留空)。pytest探测无模块的失败日志保留，没有安装新依赖。最终7方法通过见copy-count-green.txt；本子任务未跑全量。

原件14个DOCX共26页已全部用view_image打开，图像流程2张也已看。packaged render_docx实际尝试因无LibreOffice失败，日志保留。替代渲染明确CoCreateInstanceEx创建全新隐藏Word，空实例/PID/每个Document.Window.Hwnd校验、只读、宏3、禁链接、原件不保存、仅Quit自己的对象；原件实例69344，初填与final实例分别见本地隔离日志，创建前后原已有进程均保持。本批原件渲染时before为空，不声称操作了历史用户110792。

初版4件6页份数错误未通过，保留本地但排除最终审批。最终 `render-final` 下4件6页全部实际查看：申请书各2页、证据各1页；3/2份数正确，生日同一行，自己的市名和所有虚构字段正确，证据六列1条/页数3，没有裁切/重叠/缺字/破表/空白尾页。签名、日期、接收栏留空；5条静态注释和案号格保留。每份只改变word/document.xml，申请书其余20部件/证据其余11部件逐字节保持，自己的原件SHA不变。

审批只绑定document-approval.json列出的最终输出SHA及6个PNG SHA；本批短事实/单证据的视觉范围，不宣称长事实或多项证据压力场景。生成DOCX、PDF、PNG和Word进程日志仅本地留存，不入公开白名单。

## 收束

本批精确公开白名单为父目录public-file-allowlist-batch2.json；旧public-file-allowlist.json及31文件未改。7方法/包部件/18附件SHA/自身材料详情/第一批31文件完整性都核对通过。另将最初50项公共白名单和4个既有公共Python依赖复制至全新任务内目录，只有4个自身空白DOCX，没有私有原始捕获/DB/会话，7方法仍通过，记录public-copy-result.json和public-copy-tests.txt；两个结果随后加入最终52项白名单。所有浏览和渲染已结束，仅关闭自己会话。未改共享config/routes/DB/README，无Git、模型推理、Windows或Ubuntu模型启动、候选服务器、换端口或借主站发布。共享集成、候选网页验收、发布另由父线程进行，不将其状态写成通过。
