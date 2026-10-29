# 江苏 2026-10-29 自身官方发现核验

清江浦区320812、淮安区320803本批均仅发现核验，不是新增候选指南。没有生成 `guide.json`，没有注册来源或适配器，没有取得自身模板，因此没有生成件或文书版式验收。模板状态只能是 `not_found_in_checked_sources`，不能写成官方未提供。主181指南/166可生成和原24候选均不因本批增加，全国未完成。

## 真实浏览结果

独立Agent Browser会话 `js-oct29-verify`，CLI0.38.2。先由江苏省门户观察到两区自身主页，再访问各自主页；自身主页实际公共服务清单链接使用xzyl.jszwfw.gov.cn宿主、webId85/86。该跨宿主是门户真实给出的链接，页面地区、人社目录和事项计数仍各自独立，未构造或把宿主名称当地区。

清江浦区自身主页： https://haqjp.jszwfw.gov.cn/ 。自身公共服务目录： https://xzyl.jszwfw.gov.cn/jszwfw/publicservice/itemlist/gg_index.do?webId=85&themid=&deptid=&fwtype= 。完整名“劳动人事争议仲裁申请”与短词“仲裁”均显示事项0/办事指南0。清空关键词，原生选择区人社局，完整检查3页，页头33事项/80指南，未见目标仲裁实施事项。3页公共正文及全页图见320812/directory-page1-final至page3-final；关键词状态、输入值与0结果见两份search-final。

淮安区自身主页： https://haha.jszwfw.gov.cn/ 。自身公共服务目录： https://xzyl.jszwfw.gov.cn/jszwfw/publicservice/itemlist/gg_index.do?webId=86&themid=&deptid=&fwtype= 。完整名与“仲裁”也均0结果。区人社局4页完整检查，页头43事项/121指南，未见目标仲裁实施事项。4页公共正文及全页图见320803/directory-page1-final至page4-final。个人服务完整名称检索同样无目标，短词曾返回计量纠纷仲裁检定，已识别为不同事项，未作为劳动仲裁指南采集。

目录的33/43事项和80/121指南是各自页面计数，不代表劳动仲裁覆盖数，也不证明服务不存在。未取得正式指南，不能编造12栏、材料、办理机构绑定、服务编码、网上办理能力或要求。二地自身正式来源、附件和网办仍待查。

## 补充来源边界

搜索发现清江浦本区2024年劳动争议调处新闻（ https://www.haqjp.gov.cn/col/14904_253552/art/17224416/1722578818873BL6nFZHU.html ）和淮安区2025年仲裁院迁址公告（ https://www.zghaq.gov.cn/col/904_568817/art/17487072/1750319580035XG8jiYvx.html ），真实浏览器访问两者均返回 `net::ERR_CERT_AUTHORITY_INVALID`。分别doctor后12PASS/0WARN/0FAIL；未忽略证书、未改HTTP或使用替代浏览器绕过。两条补充内容不作为本批材料、机关或地址绑定。搜索还出现非政府站冒称“淮安区人社通手册”和民商事淮安仲裁委员会文书，均排除，不下载或套用。

## 图像和采集质量

初期body元素截图遗漏目录下层内容，已实际打开发现。保留中间失败图片在本地，但排除公开白名单。最终采用原生 `screenshot --full`，把工具返回的本地原图按字节复制到final路径，没有编辑页面或图片。原生翻页后等待该页独有文字；最终7页图全部view_image打开，正文、地区和页码可见。淮安3页final曾在请求完成前早取到2页正文，已以该页“保留人员职业年金待遇申领”显式等待后重新捕获；最终正文独立标记检查通过。公开白名单只绑定最后实际文件SHA。

公开JSON只存渲染后的公开正文、公开超链接、可见查询词、URL、标题和UTC时间，过滤login/jsjis/SSO/auth/token等链接。不保存HAR、HTML、请求/响应headers、cookies、登录状态、私人资料或案件。

## 可集成物与约束

可接发现队列的两份 `DISCOVERY-STATUS.json`；不可导入指南库，不创建source_id，不给予生成能力。不需要共享路由、registry或适配器改动。未来应从各区其他正式官方入口取得自身实施指南及其材料附件，再精确绑定区码、机关、task/item、来源路径/参数、附件URL/原名/SHA，并逐件生成/逐页验收。仅相同省份或字节相同不能替代地区来源证明。

公开逐文件名单和SHA见 `public-file-allowlist.json`；该名单之外的早期截图/中间捕获留本地，不提交。原件白名单为空，因为没有本区已观察下载入口。`scripts/collect-jiangsu-oct29.py --finalize`验证最终各页地区/URL/独有文字/目录计数、搜索输入和0结果、门户真实目录链接、链接脱敏和文件存在；结果见evidence-checks.json。这只是证据完整性检查，不是产品或候选网页验收。

没有Git操作、模型推理、Windows/Ubuntu模型启动、Word操作、DB写入、候选服务器启动、换端口或借主站发布；共享config/routes/README未改。浏览结束仅关闭自身会话。
