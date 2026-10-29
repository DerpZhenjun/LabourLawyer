# 余杭自身模板离线验收进度

最新验收：主代理授权在保留既有用户Word110792的条件下使用严格隔离COM。自身CoCreateInstanceEx仅新增43116，四个文档Window.Hwnd全部归属43116；宏安全3、禁止打开时更新链接、只读打开、Close(false)，结束仅Quit43116，110792仍存活。两原件7页、两填写件6页共13页已全部通过view_image逐页检查。申请书长事实不截断；案号静态标签正确；证据续页重复自身表头、十项记录完整，人工签名留空。最终release-review.json/PUBLIC-WHITELIST.json取代导出前暂定状态。离线验收通过不等于候选网页验收或发布，后两项仍未执行。

## 导出前历史进度

2026-10-29：自身来源复核和19项测试通过，Word逐页验收尚未执行，不能标记模板批准或候选网页验收通过。

已以独立 agent-browser 会话真实复核余杭自身官方指南（localInnerCode `8f1bc917-6583-4541-be13-231de0b91d0b`，source_id `b08b6dbd369b40e729e61bdc`），原生展开条件、材料、办理流程、基本信息、常见问题和线下窗口。当前仍为5材料、两空白下载控件与独立身份证示例；龙潭路22号一楼9/10号窗口、0571-89391163及60天/44工作日/5个工作日受理阶段均未变化。复用自己的既有下载原件和证明，未重新下载、未点击登录或在线办理。原有178个封存文件全部SHA未变，旧清单未重新签发。新原始DOM/HTML/快照/截图放private/，不得公开。

修复位于 `backend/regional_zhejiang_documents.py` 的证据表分支：保留静态“案号”并填写相邻值格，续页重复自身原前两行表头，证据记录保持整行、手签格留空。地区、机关、事项、附件、SHA、原下载URL与canonical路径的严格绑定保持原样，不继承上城来源。西湖具有相同封存字节和原有独立绑定，也使用此布局分支，但本轮未做西湖视觉验收。

新增 `backend/tests/test_zhejiang_release_layout.py` 两条回归，先实际RED（案号标签被覆盖、表头缺失），后实际GREEN；与既有9项adapter、8项source合计19项通过，15.980秒。原件及内存输出均校验包部件，仅允许word/document.xml改变。

`application-synthetic.docx`、`evidence-synthetic.docx`均为虚构排版测试，尚未实际Word渲染，不作为已批准交付。打包render_docx.py尝试因缺少soffice.exe失败，诊断日志已保存。协调Word时发现已有WINWORD（非本agent启动）；江苏同样在导出前检测到该进程而中止。本agent没有附着、停止或复用该进程，也未启动自己的Word COM。

`PUBLIC-WHITELIST-PREVISUAL.json`仅列可审阅的代码与安全元数据，排除生成DOCX及所有private/raw/auth/session材料。后续在主代理协调到独占Word窗口后，运行qa_yuhang.py render，只读导出两份原件与两份虚构文书；逐页view_image后才允许运行finalize_release.py --after-manual-review生成最终验收与白名单。不得在未看完所有页时调用该最终记录命令。

共享调度接口及ADAPTER名称未变，无需新增dispatcher；未改共享routes/config/README、未开公共DB、未启候选服务、未调用模型或Git。候选网页依然NOT_RUN_POLICY_REFUSAL_RETAINED；未发布，滨江材料冲突未变。
