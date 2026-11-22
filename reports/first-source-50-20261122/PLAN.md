# First-source 50-region pilot Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for shared measurement and integration. Apply superpowers:dispatching-parallel-agents only to the three disjoint source-research groups; no shared browser or overlapping writes.

**Goal:** 完成冻结50地区的首次自身来源核验，实际计算新增覆盖速度及原件新颖比例，给出有边界说明的全国工期预算，随后暂停。

**Architecture:** 独立的公开来源证据包，每个地区保留身份与耗时、来源范围、指南/材料/模板状态及原件SHA。三组独立研究15地区，Root研究5地区并负责基线、统计、独立核对及最终回执；未解决样本不替换、不伪装完成。

**Tech Stack:** 官方网站、公开网络检索、Python标准库、现有模板SHA/OOXML验收模块、隔离开发数据。

**Spec:** reports/first-source-50-20261122/SPEC.md

## Global Constraints

所有限制继承SPEC.md。已有隔离工作区D:/pl-qzdy-stage-nov08，分支codex/first-source-50-20261122；不得改动主仓库六份文件、已有封存provider及私有库。旧暂停和租约保留历史，仅本批ACTIVE。

## Review Focus

- 来源自身地区适用性：省站发布也必须明确本地实施主体及适用范围。
- 目录陈旧或重复别名：原样本保留，不把旧县名、虚拟市辖区或园区冒充新覆盖。
- 只有机构、新闻、调解、劳动监察：不得晋升完整仲裁指南。
- 模板缺失、损坏、样表或登录边界：未知独立统计，不能缩小分母制造高复用率。
- 失败和右删失：不从成功样本的均值推断未解决地区的完成期限。

## Tasks

- [x] 核对真实进程、旧租约、项目约束与两checkpoint；记录起点和保护文件，冻结50地区及选择审计。
- [x] 构建只读的已有原件摘要基线，保存本批schema、来源证据与每地区工作时钟。
- [x] group-a：河北、山西、辽宁15地区；group-b：吉林、黑龙江、山东15地区；group-c：河南、湖北、广西15地区；Root：云南5地区。逐地区留结果，不替换失败样本。
- [x] 为统计边界先写RED测试，验证精确地区覆盖、重复/新原件分母、样表排除、右删失和墙钟/工作时间区别；实现最小聚合程序，GREEN后汇总。
- [x] Root逐项核对50条身份、官方证据、材料及附件SHA；有合格新指南才形成候选覆盖，有实际适配验收才算可生成覆盖。独立复核整批，修复重要问题。
- [ ] 根据阶段吞吐和未解决样本重估全国工期；保存报告、机器结果、余项；按明确路径提交推送和核对实际CI，完成后暂停并回读checkpoint/租约。（报告已完成，提交/CI/暂停回读进行中）

封存说明：上述实测/审核已完成，最后一项的远端CI与暂停回读实际状态见本地DELIVERY.json；不得以勾选代替远端回读。
