D4候选追加与发布工具验证

本报告只说明工具的纯合成临时夹具验证通过，不表示D已追加、网页验收或发布。没有读取或写入本机实际主库、候选库、目录库或个案资料，没有调用模型、启动Word、修改服务或操作Git。真实D来源的解析、共享路由和公开来源证明由根代理继续集成验证。

新增 reviewed_oct29d_release.py，candidate_review.py只新增D_FILES、load_d_guides、append_d及17候选核验分支；原A/B/C来源集合与C发布协议保留。D加载顺序固定为姑苏320508、吴中320506、萧山330109、临安330112；江苏parse_capture(code,capture_root=root/REPORT)、浙江parse_capture(name,root=root)及每层能力与adapter检查均显式转传root。可变raw guide的can_generate等标记不能授权。

append_d仅接受候选13/194/177，追加为17/198/181，版本严格195–198，拒绝旧scope/source/history或异常sequence。before-d-extension保留两份一致SQLite备份、原manifest、精确原始guide SQLite字节及备份SHA说明。候选必须为可校验的独立DELETE-journal快照；只恢复本工具锁内确认的精确原字节，避免SQLite backup恢复改变header而让原manifest SHA失效。故障后旧manifest与库SHA仍可通过verify，失败证据不覆盖。

prepare只在新的.runtime目录创建计划；没有D/acceptance/BROWSER-RESULT.json和DOCUMENT-RESULT.json便拒绝。浏览器至少4项PASS且四个source_id/version精确匹配候选。文书须7个精确pair：两江苏各application/evidence、萧山application/evidence、临安application。逐项要求原生UI、无API replay、HTTP200、准确template/source/version、真实文件SHA、ZIP CRC、Word document/body XML、非重复的PNG页路径与SHA、页视觉PASS，并检查PNG结构CRC与实际像素解码。伪装后缀、伪PNG、坏压缩流、错误来源/版本/附件及越界路径拒绝。

apply仅接受固定8000主接口oct29d-own-localities-v1、main_default、source_bound=true、models_required=false及两新D adapter。主194/177、历史202、discovery_jobs4294为固定基线，四地各只新增一条，主版本203–206，结果198/181、历史206、候选队列28→24。所有旧公共指南、旧主当前事实、旧scope/source/history和保留队列元数据均不覆盖；目录SQLite不写入。安装或commit后的后续收据/备份故障均恢复主guide库及公共文件，并保留回滚证据。工具没有进程、重启或候选端口授权逻辑。

生命周期warning只按精确平台旧提示处理；官方时限/份数冲突、认证边界、临安ISPUBLISH=0隐藏证据材料状态保持。provider依published及网页PASS输出正确的完成验收提示，工具不把隐藏未发布材料开放为下载或生成。

真实TDD证据：初始14项因D模块不存在而RED。随后独立RED→GREEN覆盖commit后失败回滚、候选sequence跳跃、verify17计数/双DB hash、候选精确字节回滚、匹配SHA的伪PNG和坏PNG压缩流、root跨层传递。首次GREEN尝试的Windows短路径/长路径夹具比较失败已保留，夹具根改为resolve后恢复；没有访问真实库解决。所有公开日志仅替换本机路径为占位符，原始日志私有保存。

最终命令：设置PYTHONPATH=backend，运行 .venv/Scripts/python.exe -m unittest backend.tests.test_reviewed_oct29d_release -v，20项通过（54.632秒）。C历史发布测试12项通过（33.448秒）。最后备份清单补充后追加两项成功/故障恢复检查通过（4.835秒）。全部SQLite、来源、收据、DOCX和PNG都由TemporaryDirectory夹具生成，provider能力和来源证明边界mock；不将这些合成收据写入实际D验收目录。

真实D浏览器/原生下载/逐页视觉收据及实际append/prepare/apply均未由本代理运行。根代理只有在自身真实验收完成后才能执行发布；本工具PASS不能代替这些门槛。
