# Bubble Agent 面试学习与问答手册

> 目标：不是背诵框架名，而是能从业务问题、设计取舍、实现细节、故障案例和量化验证五个层次完整讲清项目。

## 1. 这个项目能展现哪些开发水平

### 1.1 能力矩阵

| 能力 | 项目证据 | 面试可证明的水平 |
| --- | --- | --- |
| Python 后端 | FastAPI、Pydantic、SQLAlchemy、Repository、异常映射 | 能独立设计和实现中小型后端服务，不只会写脚本 |
| Agent 工程 | LangGraph 状态图、interrupt、条件边、Critic、checkpoint | 理解 Agent 是状态与控制流系统，不只是拼 Prompt |
| API 与实时通信 | REST、SSE、事件游标、终态、重连 | 能根据通信方向选择协议并设计一致性边界 |
| 数据建模 | Bubble/Run/Event/Artifact、版本、双 SQLite | 能区分业务状态、运行状态与展示状态 |
| 可靠性 | 恢复、有限重试、取消、幂等思路、错误分层 | 有生产意识，知道 Happy Path 之外会发生什么 |
| 模型工程 | Provider Adapter、结构化输出、Schema 校验 | 能隔离供应商差异并约束不确定输出 |
| 前后端协作 | React 状态、确认表单、Artifact Tab、Trace | 能完成一条端到端产品链路 |
| 桌面交付 | Tauri/Rust、PyInstaller sidecar、NSIS | 理解多进程、本地权限与打包运行时 |
| 测试评测 | 9 个自动化测试、20 个固定样本、契约指标 | 能把 Agent 行为变成可回归的工程指标 |
| 产品判断 | 深度策略、MVP 边界、竞品差异化 | 能从真实问题出发控制范围，而非为技术而技术 |

### 1.2 对岗位的对应关系

应聘 **Agent / 大模型应用开发** 时，重点讲：状态图、Human-in-the-loop、结构化输出、Critic、模型适配、评测。

应聘 **Python 后端** 时，重点讲：后台任务、状态机、SSE、数据库事务、恢复、错误语义、鉴权和测试。不要让面试官以为项目只有 Prompt。

应聘 **全栈 / 客户端** 时，重点讲：React 与 Tauri 如何管理 Python sidecar、启动令牌、进程退出、开发与打包环境差异。

合理定位是：**具备独立完成一个中等复杂度 AI 应用 MVP 的能力，并已经触及生产化边界；还不是大规模分布式系统经验。**

## 2. 必背的项目介绍

### 2.1 30 秒版

“Bubble Agent 是一个本地桌面项目规划 Agent。用户输入模糊想法并选择开发深度，系统通过 LangGraph 做澄清、人工确认、方向发散收敛和 Critic 修订，生成结构化 PRD、MVP 与技术方案。后端用 FastAPI、SSE、SQLAlchemy 和双 SQLite 实现事件追踪与断点恢复，桌面端用 Tauri 打包 Python sidecar。三种深度对应真实图路径，并用 9 个测试和 20 个固定样本做回归。”

### 2.2 60 秒版

“我做这个项目是因为一句话直接交给聊天模型，通常会得到范围膨胀、前后矛盾且无法恢复的长文本。我把规划过程建模为 LangGraph 状态机：先提取事实和假设，再按 Spark、Builder、Architect 三档策略限制问题数量、决定是否发散方向、控制 Critic 轮次和产物 Schema。生成前用 interrupt 暂停，用户确认后从 SQLite checkpoint 恢复。最终事实是经过 Pydantic 校验的结构化对象，Markdown 只是渲染视图。FastAPI 将节点事件写入业务 SQLite 并通过 SSE 推给 React；Tauri 负责随机本地令牌、PyInstaller sidecar 启停和 NSIS 打包。我还做了进程重启恢复测试和 20 样本契约评测，当前全项通过。”

### 2.3 3 分钟版结构

按以下顺序展开，不要从技术栈清单开始：

1. **问题**：模糊想法直接生成会范围失控、不可追踪；
2. **核心设计**：深度是执行策略，生成前强制人工确认；
3. **主链路**：normalize → gaps → interrupt → divergence → draft → critic → persist；
4. **工程边界**：结构化对象、双数据库、SSE 事件、Tauri sidecar；
5. **验证**：7 tests、20 cases、真实 Windows installer；
6. **故障案例**：GraphInterrupt 误报或 PyInstaller/Uvicorn 导入问题；
7. **下一步**：动态端口、凭据库 UI、真实模型语义评测。

## 3. 简历写法

### 项目标题

**Bubble Agent｜基于 LangGraph 的本地可恢复项目规划 Agent**

### 三条项目描述

- 基于 LangGraph 设计深度感知的有状态工作流，将 Spark/Builder/Architect 映射为不同澄清预算、条件分支、Critic 轮次及 Pydantic 产物契约，实现人工确认中断与 SQLite checkpoint 恢复。
- 使用 FastAPI、SQLAlchemy 与 SSE 构建本地 Agent 后端，分离业务数据和图检查点，持久化节点级 RunEvent，并支持事件游标续传、Artifact 版本与 Markdown 导出。
- 使用 Tauri 管理 PyInstaller Python sidecar 和随机启动令牌，完成 Windows NSIS 安装包；以 9 个自动化测试和 20 个固定样本验证三档路由、鉴权、SSE、重启恢复及产物契约，离线契约通过率 100%。

不要写“提升 80% 效率”之类没有实验依据的数字。100% 只指当前确定性契约集，不能说真实模型质量 100%。

## 4. 业务与产品问题

### Q1：为什么要做这个项目？

因为项目早期不是缺文字，而是缺决策过程：哪些是事实、哪些是假设、要问什么、范围如何收敛、为什么选择某个技术。通用聊天记录无法稳定保存这些结构，因此需要一个可暂停、可恢复、可审计的工作流。

### Q2：竞品已经能生成 PRD，你的创新是什么？

不宣称“生成 PRD”创新。差异是组合：深度真实改变图路径；生成前有硬性人工确认；Bubble 保存业务版本和图 checkpoint；前端展示节点轨迹；默认本地运行且模型可替换。创新点可以被测试验证，不只是营销描述。

### Q3：为什么首版不直接生成代码？

生成代码会引入文件系统、Shell、依赖安装、沙箱、回滚和供应链风险，范围会从规划 Agent 变成编码平台。首版优先把需求收敛、状态恢复和评测做扎实，输出 Markdown 可交给现有编码 Agent。

### Q4：开发深度对用户有什么价值？

用户在探索阶段只需要快速判断值不值得做，正式开工前才需要 API 和数据模型。让成本与决策阶段匹配，减少“每次都生成一份巨大 PRD”。

### Q5：怎么判断 MVP 成功？

工程指标包括：三档路径和产物契约通过率、恢复成功率、Schema 有效率、节点失败率。产品指标应通过可用性测试验证：首次用户是否在 5 分钟内完成、是否减少范围回流、导出方案能否直接支持下一步开发。

## 5. LangGraph 核心问答

### Q6：为什么用 LangGraph，不用普通 Chain？

Chain 适合固定线性管道。本项目需要条件路由、人工暂停、循环评审、持久化和恢复，这些是图运行时问题。LangGraph 把状态、边和 checkpoint 作为一等概念，减少手写状态机的恢复复杂度。

### Q7：为什么不用纯 `if/else`？

小流程当然可以手写。选择 LangGraph 是因为本项目明确需要跨进程的 interrupt/resume、节点级 checkpoint 和可观察路径。若只有三步同步生成，我会用普通函数，避免框架成本。

### Q8：State 里应该放什么？

只放可序列化、恢复后仍有意义的事实：ID、输入、策略、澄清结果、回答、候选方向、结构化计划、评审问题、修订次数和错误。数据库连接、模型客户端、函数、锁等运行时对象不能放进 State。

### Q9：`interrupt` 怎么工作？

节点调用 `interrupt(payload)` 后，LangGraph 把当前 thread 状态写入 checkpointer，并通过特殊控制流结束这次 invoke。API 将 payload 保存到 Run 并标记 waiting。用户提交答案时，用同一 `thread_id` 和 `Command(resume=...)` 恢复，节点从中断点继续。

### Q10：为什么必须把 GraphInterrupt 单独处理？

它是框架实现暂停的控制流异常，不是真实失败。如果通用异常包装器把它记录成 `node_failed`，用户虽然能继续，但监控数据失真、轨迹出现错误堆栈。正确做法是先重抛控制流异常，再捕获业务异常。

### Q11：Critic 为什么不会无限循环？

两个退出条件：评审通过则结束；未通过但 `revision_count` 达到 `DepthPolicy.critic_rounds` 也必须结束并保留剩余问题。预算属于状态和策略，而不是靠 Prompt 要求模型“不要循环”。

### Q12：Critic 真的算 Multi-Agent 吗？

当前不是多个自治 Agent，而是同一有状态图中的角色化节点。可以说“Critic 节点”或“评审角色”，不要夸大成多 Agent 系统。首版有意避免多 Agent 带来的协调和成本复杂度。

### Q13：为什么先发散再收敛？

直接生成往往锁定模型最先想到的方案。Builder/Architect 先产生少量不同方向，再按价值、工作量、风险和约束匹配评分，能保留选择理由。Spark 跳过此步骤以节省时间。

### Q14：如何恢复而不重复执行之前节点？

依赖同一 `thread_id` 的 checkpoint 和 `Command(resume=...)`。业务 Run 保存 thread ID，重启后重新创建 graph/checkpointer 连接即可找到状态。恢复测试会销毁第一个 App/TestClient，再用相同 data directory 创建第二个实例并继续。

### Q15：checkpoint 和 memory 有什么区别？

Checkpoint 是运行时快照，回答“图执行到哪、State 是什么”；项目 memory 是业务事实，回答“用户确认了什么、有哪些产物版本”。前者由 LangGraph 管理，后者由业务数据库管理。

## 6. 模型与结构化输出

### Q16：如何保证模型返回正确 JSON？

不能绝对保证。系统给模型目标 JSON Schema，解析返回内容，再用 Pydantic 做类型、枚举、范围和必填字段校验。失败进入有限重试；最终失败明确标记 Run，而不是把半合法文本写成产物。

### Q17：为什么不直接保存 Markdown？

自由文本难以做字段级校验、版本比较和定向修订。结构化 JSON 是领域事实，Markdown 是确定性视图。这样同一 Artifact 未来可以渲染为 HTML、PDF 或编码 Agent 上下文。

### Q18：如何替换模型供应商？

Graph 只依赖 `StructuredModel` 协议。Demo 和 OpenAI-compatible 都实现 `generate(schema, task, context)`。供应商 URL、认证、请求格式和异常转换封装在 Adapter 内，节点不用修改。

### Q19：哪些错误应该重试？

超时、限流、临时 5xx、偶发 JSON 格式错误可有限重试；API Key 错误、权限错误、明确的输入校验失败不应盲目重试。重试要有次数和预算上限，并记录事件。

### Q20：如何防止 Prompt Injection？

当前模型没有 Shell、浏览器或任意文件工具，风险主要是产物污染而非系统接管。应把用户输入作为数据字段、固定系统规则、限制输出 Schema、避免把密钥放进上下文，并在未来接工具前增加权限、参数校验和沙箱。

### Q21：Demo Provider 有什么意义？

它是 Fake Model：稳定覆盖图路径、离线演示、低成本 CI。它只能证明工作流契约，不能证明自然语言质量。面试时主动说出这个边界会比假装它是高质量模型更可信。

## 7. FastAPI 与并发

### Q22：为什么 API 启动 Run 后返回 202？

Agent 运行可能持续较久。请求只负责创建 Run 并提交后台线程，202 表示已接受而非已完成。前端再通过状态接口和 SSE 观察执行。

### Q23：为什么使用线程池？

当前模型适配器和 LangGraph invoke 是同步接口，用有限大小线程池可避免阻塞 FastAPI 请求线程。首版最多两个 worker，符合本地单用户场景。生产多用户服务会改成异步模型客户端或独立任务队列。

### Q24：线程池有什么隐患？

进程退出会丢失正在计算的线程；Python 线程无法安全强杀正在运行的函数；CPU 密集任务受 GIL 影响；任务状态与数据库更新要防竞态。当前通过 checkpoint、安全点取消和本地低并发控制风险。

### Q25：为什么用 SSE，不用 WebSocket？

现在主要是服务端推送节点事件，客户端操作仍走普通 POST。SSE 单向语义、浏览器支持、事件 ID 和自动重连都更合适。若未来需要实时双向 token 控制、语音或协同编辑，再考虑 WebSocket。

### Q26：SSE 如何断线续传？

RunEvent 落库并有递增 ID。客户端连接带 `after_id`，也支持 `Last-Event-ID`；服务端只查询更大的事件。事件流是通知通道，终态后前端重新获取业务快照。

### Q27：为什么不能只在内存里 pub/sub？

进程重启或客户端断线会丢消息，也无法审计。数据库事件对本地单用户负载足够，换来恢复和可解释性。高吞吐时才需要 Redis Streams、Kafka 等基础设施。

### Q28：API 错误如何设计？

输入 Schema 错误由 FastAPI/Pydantic 返回 422；资源不存在映射 404；非法状态迁移返回客户端可理解的错误；模型或节点异常落入 Run.failed 和结构化事件，不把 Python 堆栈直接展示给用户。

## 8. 数据库与一致性

### Q29：为什么选 SQLite？

这是本地单用户桌面应用：零运维、事务、索引、可检查文件都比部署 PostgreSQL 合适。数据库选择要跟部署模型匹配。未来云端多用户、高并发写入时再迁移 PostgreSQL。

### Q30：业务库为什么与 checkpoint 库分离？

业务数据是稳定领域模型，checkpoint 是框架内部格式和恢复机制。分离后可以独立迁移、备份和清理，也避免 API 依赖 LangGraph 私有表结构。

### Q31：Artifact 如何版本化？

同一 Bubble 和 Artifact 类型每次持久化计算下一版本，不覆盖旧记录；查询工作台时取每类最新版本。未来 Diff 可以比较两个版本的 `schema_data`，而不是逐行猜 Markdown 变化。

### Q32：如何防止重复恢复导致重复产物？

当前通过 checkpoint 保证节点位置，并将最终写入集中在单一节点。更严格的生产方案会给节点执行添加幂等键，例如 `(run_id, node, attempt)`，并让持久化事务检查 run 是否已完成。

### Q33：Repository 模式的价值？

将 SQLAlchemy 查询、事务和 ORM 映射从 API/Graph 中隔离，测试更容易替换数据目录，业务逻辑也不会散落 SQL。代价是小项目多一层抽象；本项目的数据和恢复逻辑足够复杂，抽象是合理的。

## 9. Tauri 与打包

### Q34：为什么选择 Tauri 而不是 Electron？

Tauri 使用系统 WebView，桌面壳和安装包通常更轻，并原生支持 sidecar 权限与生命周期管理。代价是需要 Rust 工具链、WebView2 依赖和更复杂的跨语言调试。这里选择它是因为本地 Python sidecar 正好是项目重点。

### Q35：桌面应用如何启动 Python？

PyInstaller 先把 Python 服务打成单文件 exe，并按 Tauri 的 target triple 命名。Tauri Shell Plugin 启动 external binary，注入 token/data directory/host/port 环境变量，保存 `CommandChild`，窗口销毁时 kill。

### Q36：为什么要排空 sidecar 输出？

子进程 stdout/stderr 通常通过 pipe 传输。如果父进程长期不读，缓冲区可能填满并阻塞子进程。后台任务持续接收事件，即使暂时不展示也要 drain。

### Q37：本地 HTTP 服务安全吗？

只绑定回环地址，外部网络无法直接访问；每次 Tauri 启动随机生成 token，API 使用常量时间比较。它仍不是绝对安全：同一用户权限下的恶意进程可能读取进程信息或抢端口，因此还应采用动态端口、最小权限、日志脱敏和系统凭据库。

### Q38：为什么打包后 Uvicorn 启动失败？

开发态传入 `"bubble_agent.main:app"`，Uvicorn 会按模块路径二次导入；PyInstaller 单文件环境不保留同样的源码导入上下文。改为直接传递已经创建的 `app` 对象后解决。这个案例说明必须测试最终产物，开发构建通过不等于可交付。

### Q39：安装包如何构建？

先生成图标，再用 PyInstaller 构建带 target triple 的 sidecar，然后 Vite 构建前端，Cargo release 编译 Tauri，最后由 NSIS 生成 current-user installer。

## 10. 测试与 Agent 评测

### Q40：普通单元测试和 Agent 评测有什么区别？

单元/集成测试验证确定性契约，例如状态码、节点路径、Schema 和恢复；Agent 评测还要验证概率性输出质量，例如相关性、一致性、范围和事实性。二者都需要，不能用“模型有随机性”逃避工程测试。

### Q41：20 个样本的 100% 代表什么？

代表 Demo Provider 下七项工作流契约全部满足，包括深度路由和产物集合；不代表真实模型生成内容 100% 正确。评测报告明确写出适用边界。

### Q42：为什么不直接用 LLM-as-judge？

首个基线先覆盖完全可判定的契约，成本低且结果稳定。Judge 适合评价主观质量，但有偏差、位置效应、模型泄漏和成本问题，应结合人工标注并校准，而不是取代规则测试。

### Q43：如何设计真实模型评测集？

每个样本标注必须询问的信息、禁止假设、MVP 功能上限、明确 out-of-scope 和期望 Artifact。分别运行各深度，记录 Schema 成功率、范围回流率、术语一致性、延迟、Token 和人工评分。

### Q44：如何测试恢复？

第一个应用实例创建 Run 并停在 waiting，然后完整关闭 TestClient；第二个实例使用同一 data directory 重建 DB engine、repository 和 checkpointer，再对原 Run resume，断言完成且产物存在。

### Q45：还缺哪些测试？

真实网络超时与限流、SSE 中途断线和 Last-Event-ID、并发点击 resume、运行中取消、数据库写失败、端口占用、sidecar 意外退出、凭据不落盘扫描、安装后首次启动。这些是下一阶段最有价值的补充。

## 11. 故障与复盘故事

### 故事一：正常 interrupt 被当成失败

- 现象：UI 能进入等待，但 Trace 出现 `node_failed` 和长堆栈；
- 定位：通用节点装饰器捕获了 LangGraph `GraphInterrupt`；
- 根因：把框架控制流异常和业务异常混为一类；
- 修复：显式重抛 GraphInterrupt，只记录真实异常；
- 防回归：等待阶段断言事件中不存在 `node_failed`；
- 反思：可观测数据本身也需要正确性测试。

### 故事二：源码能运行，sidecar 不能启动

- 现象：PyInstaller 成功，但健康检查超时；
- 定位：前台运行可执行文件，得到 ASGI 模块导入失败；
- 根因：Uvicorn 字符串路径依赖运行时再次 import；
- 修复：直接传 ASGI app 对象；
- 验证：真实 exe 启动，health=ok，无令牌请求=401；
- 反思：构建成功不是发布成功，必须冒烟最终二进制。

### 故事三：Tauri 首次编译暴露多类错误

- 缺失 Windows 图标；
- `serde_json` 宏依赖缺失；
- 本地变量遮蔽 command 函数；
- Mutex 临时 guard 生命周期不满足借用检查。

处理方式是逐个让编译器缩小问题，而非猜测。最后 `cargo check` 和 release/NSIS 构建均通过。

## 12. 高频追问的短回答

### 为什么叫 Bubble？

表示一个持续演进的项目上下文容器，但与 Bubble.io 品牌冲突，所以只是工作代号，公开发布前会更名。

### 为什么不用 Celery？

本地单用户应用不值得引入 broker 和 worker 运维。线程池加 checkpoint 足够；云端多实例时才考虑任务队列。

### 为什么不用 Redis？

同理，SQLite 已覆盖持久事件与状态。架构复杂度应与负载匹配。

### 为什么前端结束后还要重新 GET？

SSE 是通知，不是唯一事实。终态后读取数据库快照可以解决丢事件、重复事件和前端状态不完整。

### 为什么要有 RunEvent？

用户可解释、开发调试、断线续传、评测统计和面试演示都需要统一事件模型。

### 为什么 API Key 不保存在数据库？

数据库和导出文件更容易被复制或提交。当前只从环境读取；后续配置页应只保存 credential reference，实际 secret 进入系统凭据库。

### 当前最大的技术债是什么？

固定端口、真实模型语义评测不足、凭据 UI 未实现、运行中 HTTP 请求不能立即取消、数据库迁移尚未引入 Alembic。

### 如果有两周继续做什么？

先做动态端口和健康启动门控，再做 keyring 配置页与真实模型评测；随后补 SSE 断线/并发恢复测试和 GitHub Actions Windows 构建。

### 如果用户量变成 10 万？

桌面本地架构不是直接扩容对象。云端化需要 PostgreSQL、独立任务队列、对象存储、分布式事件总线、租户鉴权、配额、幂等键和观测平台。Agent graph 可以保留，但 persistence 和 execution runtime 要替换。

## 13. 不要说错的地方

- 不要说“使用了多 Agent 协作”；当前是单图中的角色化节点。
- 不要说“完全解决幻觉”；只能通过确认、Schema、Critic 和评测降低风险。
- 不要说“100% 准确”；100% 是确定性契约评测。
- 不要说“支持所有模型”；当前支持 Demo 和 OpenAI-compatible 协议。
- 不要说“支持完全实时取消”；当前取消在安全检查点生效。
- 不要说“API Key 已接系统凭据库”；当前安全方式是环境变量，配置 UI 是后续项。
- 不要说“生产级分布式系统”；这是本地单用户、生产意识较强的 MVP。

## 14. 面试前代码走读路线

按这个顺序读，约 90 分钟：

1. `domain/schemas.py`：先理解领域对象和状态枚举；
2. `agents/policies.py`：理解三档深度契约；
3. `agents/state.py`：理解图内存；
4. `agents/graph.py`：画出节点、条件边和 interrupt；
5. `services/orchestrator.py`：理解后台执行与业务状态；
6. `persistence/models.py`、`repositories.py`：理解数据边界；
7. `api/runs.py`：理解 SSE 和终态；
8. `models/openai_compatible.py`：理解结构化调用和异常；
9. `src-tauri/src/main.rs`：理解进程、令牌和退出；
10. `tests/`、`evals/run_evals.py`：理解如何证明正确。

每读完一个文件，用四句话回答：它解决什么问题、输入输出是什么、失败如何表现、为什么不放在别层。

## 15. 白板题准备

面试官让你画架构时，只画以下五块：UI/Tauri、FastAPI、Orchestrator/LangGraph、Model Adapter、双 SQLite。箭头标出 HTTP/SSE、spawn/kill、checkpoint、business persistence。

让你画状态机时画：

```text
draft → queued → running → waiting → queued → running → completed
                    └──────────────→ failed
                    └──────────────→ cancelled
```

然后说明 Bubble 状态和 Run 状态不同：一个 Bubble 可以有多次 Run，Bubble 显示面向用户的整体状态，Run 记录某次执行。

## 16. 自测清单

面试前确保能脱稿回答：

- 我解决的不是“生成文字”，而是什么决策问题？
- 三档深度具体改变哪五个参数？
- interrupt、checkpoint、resume 的数据如何串起来？
- 为什么业务 SQLite 和 checkpoint SQLite 要分离？
- 为什么选择 SSE，断线如何续传？
- Pydantic 在模型边界和 API 边界分别做什么？
- Artifact 为什么同时保存 JSON 和 Markdown？
- Critic 如何退出，如何避免无限循环？
- Tauri 如何安全启动和回收 Python sidecar？
- 两个真实故障的现象、根因、修复、验证是什么？
- 20 样本的 100% 能说明什么、不能说明什么？
- 当前三项最大限制和下一步优先级是什么？

如果这十二题都能用“结论—证据—取舍”回答，这个项目就足以支撑一轮有深度的 Agent 或 Python 后端项目面。
