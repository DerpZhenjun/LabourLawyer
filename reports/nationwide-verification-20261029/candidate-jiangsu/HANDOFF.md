# 江阴、宜兴候选站实际验收完成

最终结果：17项真实MCP UI/HTTP检查通过；另有Agent Browser原生下载6份PK/CRC/SHA通过；四份实际生成件共6页已隔离Word渲染并逐页查看通过。本任务未发布，供root按既定发布流程整合。

- 江阴320281：source_id=3d304f186983f34c4170a398，实际API version=186。
- 宜兴320282：source_id=509219666f61612819e02f36，实际API version=187。
- 实际UI省份/城市/区县选址、默认虚构填写、取消/Escape不产生POST、确认后申请及证据POST200、响应源ID/Word类型正确。
- 实际输入生日1991-05-09、副本3、证据2。两区实际下载申请书的Word XML及渲染页均显示相同值，签名和日期保持空白。两区证据默认1项，实际添加到2项再删除回1项，生成清单一行内容完整。
- 两地申请与证据375/768/1440的document/body scrollWidth均不超过innerWidth；console error/warn均0。错误虚构区名清除source与form，不继承上一地指南。

## 实际下载与逐页检查

专用Agent Browser会话js-candidate-binary-oct29，只用原生点击、填写和确认；wait --download在本Windows版本返回的目标路径并非实际落盘路径。按root发现的方法，在本专用会话另开chrome://downloads，只读自身downloads-item，严格匹配state=2、自己的loopback模板URL或blob URL、地区/文书文件名，取得精确filePath后复制到.runtime。没有枚举用户下载目录，没有HTTP replay。旧会话关闭后记录为空，因而没有猜测历史文件；后续文件都由当前会话记录证明。断点恢复仅复核同任务已捕获文件，resumed_existing_own_captured_file明确标注。

6份原生下载：两区各自身申请书原件、生成申请书、生成证据清单。两区各原件17701字节，SHA256=99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3，分别与各自此前正式指南的原件证明匹配；不是借邻区。生成申请书各12757字节，SHA256=d3a535057c0d05400e30568fff34dd8026a1fed95d31423cef0a02844da2b47d；证据清单各11563字节，SHA256=a0dfc4f7696258c56fb1fd4b79072af7b1f7862920f150a966c1500149b0b8a0。两区空白字节和虚构输入相同，故生成SHA相同；各自UI源ID、原件URL和Chrome下载记录分别绑定。

原MCP BROWSER-RESULTS.json的17项和二进制false记录保持原样，因为当时文件确为0字节。新增ACTUAL-DOWNLOAD-RESULTS.json、ACTUAL-DOCUMENT-QA.json及ACCEPTANCE-SUMMARY.json记录独立原生下载已补齐的事实，不能把先前MCP阶段改称二进制成功。

使用既有隔离Word只读导出4份实际生成件，新PID8204及四个document HWND匹配，宏禁用、打开链接更新关闭、只退出已证实的新对象。申请书各2页、证据各1页；Poppler110dpi转换后6页全部查看，无裁切、重叠、缺字或表格断裂。Word资源已交还其他agent，不再占用。

## 文件与操作边界

公开只复制PUBLIC-WHITELIST.json明示文件及清单本身。所有原始payload、完整transcript、Chrome下载记录精确路径、实际DOCX、PDF、PNG和Word实例完整证据只在.runtime/candidate-browser-20261029/js/，禁止公开。公开结果仅摘要、哈希和页面检查结论；客户端数据全部为虚构例子。

未编辑共享config/routes/DB/README或冻结江苏文件；未启动/关闭候选服务、未调用模型、未执行Git。本任务专用浏览器已关闭。可复核脚本为verify-jiangsu-oct29-candidate.mjs及verify-jiangsu-oct29-downloads.py。
