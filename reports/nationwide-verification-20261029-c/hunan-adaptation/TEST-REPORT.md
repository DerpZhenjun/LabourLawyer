湖南C独立申请书适配与文书检查

雨花430111与望城430112分别读取本轮自身封存指南、公开目录、下载控件、原件及网办边界。原175项公开文件逐字节复核全部不变；没有重新采集、改封存manifest、借用B地区规则或来源身份。两个地区各4材料、2空白DOC及2样例DOC保留。两区劳动者原DOC同SHA，但各自从自己的原件独立转换，并绑定自身approve_id、机关、事项、材料、附件与原件/转换SHA。转换DOCX明确为平台副本，不是官网下载DOCX。

接口为 backend/regional_hunan_oct29c.py 的 ROOT、REPORT、SPECS、ADAPTER、parse_capture(name,capture_root=None)、blank_binding(guide,template,root=None)、with_capabilities(guide,root=None)、fill_document(guide,template,'application',ROOT/template['file'],data)。ADAPTER为 hunan_own_legacy_worker_oct29c_v1。root参数仅查对应公开目录，无私有或旧地区fallback。公共root实际复制175公开文件、封存清单和派生件后运行通过，篡改原页或缺件即关闭能力。发布、store版本、warnings等生命周期字段不参与官方事实绑定。

只开放各自劳动者空白申请书。附随证据位于申请书内，不开放单位申请版或独立证据清单。数据严格使用 frontend/src/data/hunanApplicationFields.js 的27 keys与现有 HunanApplicationRequest：24普通字段最多160字符、8项请求、事实1800字符、10项附证且每项仅name/source/purpose各300字符。身份证号、签名输入、address等旧别名、未知键与XML非法字符拒绝。签名空位保持，不自动签名。日期按可解析日期填年月日，无法解析的普通文字原样填对应槽，不静默丢弃。

TDD-RED.txt记录新provider不存在时的真实失败；TDD-GREEN.txt为9项通过。命令：设置PYTHONPATH=backend，运行 .venv/Scripts/python.exe -m unittest backend.tests.test_hunan_oct29c -v。检查覆盖两区独立身份、同字节错区拒绝、错附件、官方事实缺失或改写、派生缺失、无源root、纯公开root、未知字段与容量、任意路径、证据kind拒绝及原件不变。

使用documents技能；authoring marker成功一次，预期6份DOCX（自己的转换2份与合成检查生成4份）。packaged render_docx.py失败日志明确缺少soffice.exe，未重复尝试安装或改用户Word。随后通过独立空Word实例，禁宏、禁链接更新，核对每个文档窗口属于自己的新实例，读取原件导出PDF与另存转换副本；生成件也在另一次独立实例只读导出。两次均退出自身实例，未碰用户Word；公开隔离摘要移除实际PID，原始过程记录仅在.runtime保留。

4唯一原件共14页逐页view_image（空白劳动者4、空白单位4、劳动者样例3、单位样例3）。望城4份原件SHA与雨花4份对应相等，仅复用这些已看图的字节检查；DOCUMENT-QA.json逐项列出原件SHA和每页SHA。样例中的开福地址和1997.10.32原样留存，不进入生成内容。

两个地区各生成normal2页、maximum22页，共48页全部逐页view_image。maximum同时使用24普通字段各160字、8请求各160字、事实1800字、10附证且每项3字段各300字；文字完整、自动分页、无裁切或重叠。900字附证保持同一页，末尾余白为防止拆散一项证据所致。普通示例保持2页。四份生成包与各自转换源比较，仅word/document.xml变化，其余ZIP条目逐字节不变。A4纵向、原字体/边距/表格/说明/手签空位保留，不套新样式。

本代理未做共享路由、前端、DB、服务、Git操作，未调用任何模型或启动Windows模型。网办只证明进入本区官方统一认证；未登录、未提交，登录后能力未核验。候选网页、实际API集成及上线由根代理继续验收，不由文书检查报告宣称完成。单位版和独立证据清单未适配，官方时限/份数等矛盾继续依自身指南原文保留。

PUBLIC-WHITELIST.json明确列出本次provider、测试、新派生、纯合成输入和QA证据的SHA及字节数；旧来源封存目录不在本次写入范围。
