# Bubble Agent 离线评测报告

> 评测使用确定性 Demo Provider，目标是验证工作流、深度策略、产物契约和恢复边界；它不代表线上大模型的语义质量。

## 摘要

- 样本数：20
- 全项通过：20/20
- 平均契约得分：100.0%
- P95 端到端耗时：257 ms

## 检查维度

1. 进入人工确认中断；2. 澄清问题不超过深度预算；3. 正常完成；4. 产物类型符合策略；5. Markdown 非空；6. 无节点失败；7. 分支与 Critic 路径符合深度策略。

## 样本结果

| 样本 | 深度 | 得分 | 耗时 | 失败项 |
| --- | --- | ---: | ---: | --- |
| student-planner | builder | 100% | 253 ms | — |
| meal-prep | spark | 100% | 159 ms | — |
| elder-medication | architect | 100% | 129 ms | — |
| campus-lost-found | builder | 100% | 159 ms | — |
| interview-review | builder | 100% | 257 ms | — |
| pet-health | architect | 100% | 203 ms | — |
| reading-club | spark | 100% | 171 ms | — |
| freelancer-crm | architect | 100% | 202 ms | — |
| lab-inventory | builder | 100% | 200 ms | — |
| travel-split | spark | 100% | 154 ms | — |
| bug-triage | architect | 100% | 159 ms | — |
| community-events | builder | 100% | 161 ms | — |
| resume-tailor | architect | 100% | 194 ms | — |
| focus-room | spark | 100% | 178 ms | — |
| support-kb | architect | 100% | 198 ms | — |
| secondhand-books | builder | 100% | 198 ms | — |
| habit-experiment | spark | 100% | 161 ms | — |
| meeting-actions | architect | 100% | 194 ms | — |
| volunteer-match | builder | 100% | 200 ms | — |
| home-energy | spark | 100% | 168 ms | — |

## 如何解读

该评测把可确定验证的工程契约与主观的内容质量分开。接入真实模型后，应新增人工或 LLM-as-judge 维度，例如问题相关性、MVP 可执行性、技术栈论证质量与幻觉率，并保留本报告作为回归基线。
