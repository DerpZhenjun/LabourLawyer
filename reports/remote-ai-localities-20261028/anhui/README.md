# 庐阳区自身来源采集，2026-10-28

本批只新增安徽省合肥市庐阳区候选，不发布、不更新公共库/目录/共享registry。庐阳区自身指南可以访问，因此没有为了补数转采瑶海。真实 Agent Browser 独立会话为 `remote-ah-20261028-bce456318685`，结束已关闭。未启动服务、Word或模型，未使用Git。主发布181指南/166可生成不受本候选影响。

正式指南：<https://hf.ahzwfw.gov.cn/bog-bsdt/static/workProcess/components/applicationMaterial.html?ssqdCode=da27275dce0645ffb87c9d9423e84452>。官方搜索按 `xzqh=340103000000` 检索“劳动人事争议仲裁申请”，真实点击事项后公开地区选择 iframe 仅列【庐阳区】自身事项；`luyang/search/official-locality-selection.json`保留原始iframe HTML、文字、来源与目标URL，`selection.png`保留实际页面。

- 地区：安徽省 / 合肥市 / 庐阳区，官方12位码 `340103000000`。
- 实施机关：合肥市庐阳区人力资源和社会保障局。
- 基本编码：`002014302002`；实施清单编码：`113401037608378827400201430200201`。
- 本项目按来源URL计算的source_id：`d52d1fced81cbcacb208b7b0`。
- 正式指南55原始字段、3项材料、3份附件（空白申请书DOC、示例申请书DOC、流程图PNG），全部保持本区附件ID和原文件名。

`luyang/normalized-guide.json`从本次原始DOM表格、六个正式栏目、三个材料详情、时限说明及公开component逐项对照形成；每个字段/材料保留路径、SHA、来源时间。`build_candidate.py`是离线证据整理脚本，**不是已注册的运行时parser**。它实际核对来源URL/机关/区划/实施清单、材料表与详情、各附件ID/路径/大小/原字节SHA，没有读取旧蜀山/包河候选来推导本区要求。`staging-candidate.json`记录精确路径及SHA，`can_generate=false`，网页/生成/渲染均`NOT_RUN`。

## 材料与来源冲突

材料表原文：劳动人事争议仲裁申请书“原件或复印件，原件2份,复印件2份”；居民身份证“原件和复印件，原件1份,复印件1份”；证据“原件或复印件，原件2份,复印件2份”，均为纸质或电子、必要、申请人自备。填报须知原文另称窗口提供原件、网上提供电子件；材料依据写按被申请人人数提交副本。保留这些各自范围，不统一改成固定实务份数。

法定表格为“45个工作日”，真正点击说明弹窗写受理之日起“四十五日”，复杂可延长且不超过十五日；承诺“1个工作日”说明弹窗正文为空；流程表仅受理0.3/审查0.4/办结0.3工作日。不能把承诺字段表述为仲裁总期限。FAQ同时含“一年”和“60日”时效表述，已经作为来源冲突记录，未转成用户期限指引。基本信息的收费为否、中介栏目为本事项不涉及中介服务。

窗口原文：安徽省合肥市庐阳区北二环与大房郢路交口庐阳区政务服务中心人社综合窗口。时间原文：正常工作日上午9:00~12:00，下午12:00~5:00。咨询0551-65699354，监督0551-65699505。未修正原文时间格式。

## 在线与隐私边界

正式指南广告字段写网上办理、窗口办理及四级全程网办；真实在线办理停在统一认证登录。回调仅为通用`/bog-bsdt/transition.html`，没有证明精确事项可线上提交。公开证据是`luyang/online-check-corrected.json`及空白登录页截图；无账号、密码或验证码输入，未登录后继续。隐藏验证码控件存在，但截图中的验证码未显示；不将其误称为已遭遇可见验证码挑战。

`.private-sealed/`内的搜索全页DOM含URL路径session上下文；公开component与流程图预览DOM含附件accesskey；登录DOM含隐藏登录票据。以上保持原字节私有封存，独立`.gitignore`排除，不列入公开白名单，绝不重新计算成公开“原始无敏感”内容。公开component是明确标注转换的`public-component-without-url-queries.json`，仅去除URL查询，保留原始component SHA。实际附件下载的完整URL私有封存；公开下载manifest保留去查询地址、完整URL SHA、时间、状态、原始文件名与SHA。

下载请求只使用User-Agent/Referer，无CookieJar、Cookie或Authorization。三个响应存在Set-Cookie，但其值从未写入任何记录；只记录“值未保存”的事实。没有将响应头复制到候选或归一化指南。不能据此认定附件accesskey或登录票据匿名安全。

## 尝试记录与验收边界

`statutory-time-explanation/`及`promise-time-explanation/`是hover未展开说明的早期尝试；真正弹窗证据为`statutory-explanation-dialog/`与`promise-explanation-dialog/`。第一次切栏目被尚未关闭的法定说明遮挡，`conditions/`和`materials/`因此仍是原弹窗，不能当对应栏目成功。成功文件为`conditions-success/`及`materials-success/`。这四组早期尝试保留但不入发布白名单。每次浏览器错误后实际doctor --offline --quick均为7pass/0warn/0fail，关闭覆盖层并等待动画后才重试。

`online-check.json`的初始“非hidden input有默认值”统计未限定凭证控件，不能当账号输入；修正记录限定可见text/password/tel/email，全部为空。旧统计不列公开白名单。

已查看正式材料表、流程表与登录页截图，属于来源页面核对。未查看/转换/填写DOC内容，未调用Word、渲染或生成文书；不能断言官方“空白”文件实际无示例信息，也未批准任何省级/邻区profile复用。原件分类严格按官方标签与实际下载分开。

`PUBLIC-SOURCES.json`是本区可交主代理安全筛选的精确路径/大小/SHA清单，排除私有封存、早期失败尝试、缓存和过时统计。该白名单不是发布授权或文书适配通过。最终公开文件扫描与副本字节核对见`EVIDENCE-AUDIT.json`。
