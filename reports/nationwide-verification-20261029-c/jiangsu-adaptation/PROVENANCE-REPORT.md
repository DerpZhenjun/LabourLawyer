# C4公开来源证明

新增 `backend/regional_oct29c_public_provenance.py` 和8项测试。旧 `backend/regional_public_provenance.py` 仅在两个公开入口各增加3行lazy委派，其A/B六profile验证逻辑保持原样。未改路由、生成器、前端、来源封存清单、服务或数据库。

C4均使用调用方明确给定root，先核验原封存SOURCE-MANIFEST/PUBLIC-WHITELIST固定SHA及本区全部公开文件实际字节、大小和路径包含关系，再调用本区parse_capture(root/REPORT)重建canonical。没有默认原仓库、样例或私有材料旁路。字段、材料、机关、事项、地区、source_id、source URL、原附件类别与SHA都是事实字段。平台发布/版本信息不改变事实证明；模板的适配器、生成类型标签、严格绑定、版式状态等只接受canonical或能力提供者及标准路由包装给出的精确值，任意marker不能掩盖改动。

湖南雨花/望城在公开evidence与原件授权中均额外核验自身hunan-adaptation固定DERIVED-MANIFEST、该区原DOC和确切worker.docx字节与公开allowlist，转换件路径限定本区，拒绝将派生件冒充官方原件。江苏原件下载仅允许原封存公开名单8份blank与2份flow；8份reference_sample_not_distributed即使临时目录有同名文件也拒绝下载，不能伪装downloaded。

先运行真实公开副本测试出现C缺失两项RED，再实现GREEN。最终C8项加旧A/B11项共19项，26.404秒通过，其中2项Windows符号链接创建因系统权限跳过；没有冒称符号链接运行验收通过。测试目录仅复制公开白名单，没有backend源码或江苏sample文件；覆盖18个允许原件、8个江苏拒绝sample、精确能力标记与发布后证明、事实/来源/材料篡改、任意reports路径、实际附件损坏、缺失转换链、空root/no fallback、未分发样例同名文件。报告原始日志为provenance-RED/GREEN.txt。没有运行Word或模型。
