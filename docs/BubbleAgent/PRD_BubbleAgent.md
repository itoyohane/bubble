# Bubble Agent 项目调研与开发文档

> 项目代号：Bubble Agent（暂定）
> 项目类型：个人实习 / 校招作品
> 目标岗位：Agent 开发、Python 后端开发
> 文档版本：v0.1
> 调研日期：2026-07-20

## 1. 项目摘要

Bubble Agent 是一个本地优先的桌面端 Agent。用户输入一个模糊的产品想法并选择开发深度，系统通过澄清、发散、收敛、评审等步骤，生成 PRD、MVP 范围和技术栈建议，并将对话、决策、产物与 Agent 执行记录保存在一个持续演进的“Bubble”中。

该项目不以“一句话生成完整应用”为目标。首版重点展示：

- 使用 LangGraph 编排有状态、可恢复的 Agent 工作流；
- 使用 FastAPI 实现异步、流式、可观测的 Python 后端；
- 用结构化输出、人工确认和自动评审降低 Agent 幻觉；
- 让不同“开发深度”对应真实的图分支、评审轮次和产物集合，而不只是更长的 Prompt。

一句话定位：**将模糊想法转化为可追踪、可恢复、深度可控的项目方案的本地桌面 Agent。**

## 2. 竞品调研

### 2.1 调研结论

市场已经存在大量“想法转 PRD”或“想法转应用”的产品，因此“自动生成 PRD”本身不构成差异化。最接近本项目的是 Ideate 与 Ombuto Code：它们同样采用桌面端形态，并覆盖从想法、规划到 Agent 开发的流程。

本项目适合切入一个更小但更适合面试展示的组合：**开发深度路由 + Bubble 项目记忆 + 人工确认 + 执行轨迹 + 本地模型自由度**。

### 2.2 同类产品对比

| 产品 | 形态与主要能力 | 与本项目重合点 | 可借鉴 / 可区分之处 |
| --- | --- | --- | --- |
| [Ideate](https://github.com/kevinelliott/ideate) | 开源 Tauri 桌面应用；想法生成 PRD；支持顺序、并行和手动构建模式，并管理 Agent 执行 | 桌面端、想法转 PRD、项目空间、Agent 工作流 | 最接近的竞品。本项目首版不进入代码执行，重点把深度路由、状态恢复和评测做扎实 |
| [Ombuto Code](https://github.com/FrancoisBotha/ombutocode) | Electron 桌面工作台；覆盖 Plan、Build、Review，包含 PRD、架构、任务和编码 Agent；目前仍为 Beta | 需求规划、文档树、Agent 驱动流程 | 功能很重。本项目应控制范围，用更清晰的 Agent 状态图和本地可追踪性形成区别 |
| [Norvo](https://norvo.pro/) | Web 产品；通过澄清问题生成 PRD、技术栈、API、任务等文档包，并带评审与版本能力 | 澄清式对话、多文档、技术栈建议 | 说明“生成文档包”已有直接竞争；本项目应突出桌面、本地状态和图执行过程 |
| [IdeaPico](https://ideapico.com/) | 将想法整理为 product、tech、design、ship 四类文档，再交接给 Codex、Cursor 等编码 Agent | 从模糊想法到 Agent-ready 规格 | 可借鉴“面向下游 Agent 的结构化交付”；首版只导出 Markdown，不做外部 Agent 自动交接 |
| [Specd](https://specd.app/how-it-works) | 可选择项目阶段与技术栈，生成受 5 个功能和 1200 字约束的 PRD | 阶段选择、范围约束、技术栈 | 证明“深度/阶段选择”有需求。本项目让该选择真正改变 LangGraph 路径，而非只改变模板 |
| [ChatPRD](https://www.chatprd.ai/product/features/write-prd) | 面向产品经理的 AI 文档平台；支持项目上下文、模板、版本和多种集成 | 项目上下文、PRD、持续迭代 | 更偏团队文档生产。本项目聚焦开发者个人、本地桌面和技术方案推导 |
| [Dyad](https://www.dyad.sh/) | 本地、开源的桌面 AI App Builder，可选择多种模型并拥有代码 | 本地桌面、模型自由、从想法开始 | Dyad 的核心结果是可运行代码；本项目的核心结果是经过约束和评审的开发方案 |
| [Bubble](https://bubble.io/ai) | 成熟的无代码与 AI 应用生成平台，可从 Prompt 生成并迭代应用 | 名称及“想法到应用”的语义冲突 | “Bubble”不适合作为最终公开名称，容易造成品牌和搜索混淆，建议只作项目代号 |

### 2.3 建议定位

不应宣称某个单点能力“市场首创”，而应强调以下组合创新：

1. **深度即执行策略**：轻量、标准、深入三档分别映射到不同节点、问题上限、评审轮次和输出 Schema。
2. **发散—收敛—批判闭环**：先生成多个方向，再依据用户目标和约束评分收敛，最后由 Critic 节点检查矛盾、越界与遗漏。
3. **Bubble 可追溯记忆**：不仅保存聊天，还保存假设、用户确认、图检查点、结构化产物版本和评审结果。
4. **可解释的 Agent 运行**：前端可看到当前节点、耗时、模型调用、重试和修改原因，便于调试和面试演示。
5. **本地优先、模型可替换**：项目数据保存在本机，模型层使用适配器兼容 DeepSeek、通义千问及其他 OpenAI-compatible API。

## 3. 轻量 MVP PRD

### 3.1 项目名称

Bubble Agent（工作名；发布前需要更名）。

### 3.2 背景与问题

开发者经常只有一个模糊想法，不清楚目标用户、MVP 边界和技术路线。直接把一句话交给通用聊天模型或编码 Agent，容易得到范围膨胀、前后矛盾、难以复用的长文本；聊天结束后，关键决策和项目上下文也容易丢失。

### 3.3 目标用户

- 有产品想法但缺少产品梳理经验的学生开发者；
- 准备用 AI 编码工具开发 Side Project 的个人开发者；
- 希望快速形成可评审项目方案的初级产品或研发人员。

首要用户是：**正在准备 Agent / Python 后端面试，希望把一个想法快速整理成可实现项目的学生开发者。**

### 3.4 MVP 目标

用户能在 5 分钟内从一句模糊想法得到一套范围明确、结构一致、可继续编辑的项目方案；应用重启后仍可继续同一个 Bubble，并能查看 Agent 如何得到结果。

### 3.5 核心场景

1. 用户新建 Bubble，输入项目想法并选择开发深度。
2. Agent 分析信息缺口，提出少量高价值问题。
3. 用户确认目标与边界后，Agent 继续生成对应深度的产物。
4. Agent 自动检查范围、术语和技术选型是否一致，必要时修订。
5. 用户查看 PRD、MVP、技术栈和执行轨迹，并导出 Markdown。
6. 用户以后重新打开 Bubble，通过对话补充约束并生成新版本。

### 3.6 开发深度

| 深度 | 适用场景 | 最大澄清问题数 | 产物 | 自动评审 |
| --- | --- | ---: | --- | ---: |
| 轻量 / Spark | 快速验证一个想法 | 2 | 项目摘要、目标用户、MVP 功能、本版不做 | 规则校验 |
| 标准 / Builder | Side Project 开发准备 | 5 | 轻量全部内容、PRD、用户故事、技术栈、风险 | 1 轮 Critic |
| 深入 / Architect | 面试展示或正式开工前评审 | 8 | 标准全部内容、数据实体、API 草案、开发阶段、测试策略 | 最多 2 轮 Critic + 用户终审 |

深度参数必须通过 `DepthPolicy` 进入图状态，决定条件边、Token 预算、产物 Schema 和评审次数；禁止只把“写得更详细”拼进 Prompt。

### 3.7 用户故事

- 作为学生开发者，我希望只输入一个不完整想法也能开始，以免被复杂表单阻挡。
- 作为项目发起者，我希望控制方案深度，以便在快速探索和详细规划之间平衡时间与成本。
- 作为用户，我希望在生成前确认 Agent 理解的目标和边界，避免生成一整套错误文档。
- 作为开发者，我希望看到每一步的状态和修改原因，以判断 Agent 是否可靠。
- 作为回访用户，我希望重新打开 Bubble 后继续上次讨论，而不必重复背景。
- 作为编码 Agent 用户，我希望导出结构清晰的 Markdown，作为后续开发上下文。

### 3.8 功能范围

#### P0：必须完成

- Bubble 的新建、列表、打开、重命名和删除；
- 想法输入与三档开发深度选择；
- LangGraph 澄清、确认、生成、评审和持久化流程；
- PRD、MVP、技术栈的结构化生成与 Markdown 渲染；
- 人工确认、拒绝和补充信息后恢复执行；
- Agent 节点状态与流式文本展示；
- 本地持久化、历史版本和 Markdown 导出；
- 模型配置、连通性测试和敏感信息安全存储；
- 基本错误处理、超时、重试和取消。

#### P1：时间允许再做

- 两个方案分支的对比与择优；
- 从旧检查点创建方案分支；
- LangSmith 可选追踪；
- 产物差异对比；
- 本地技术栈目录检索工具。

### 3.9 本版不做

- 自动生成或执行项目代码；
- Shell、浏览器和任意文件系统工具调用；
- 多个自治 Agent 并行协作；
- GitHub、Cursor、Codex 等外部平台自动交接；
- 登录、云同步、团队协作和计费；
- 向量数据库与大规模 RAG；
- 移动端及跨设备同步；
- 自动部署生成的项目。

### 3.10 成功指标

- 三种深度均能生成规定的产物集合，深度路由自动化测试通过率 100%；
- 20 个固定测试想法中，结构化输出最终校验成功率不低于 95%；
- 应用在人工确认点或模型调用失败后，可从最近检查点恢复，不重复已完成节点；
- 20 个测试样本中，至少 85% 不出现明确标记为“本版不做”的功能回流到 MVP；
- 首次使用者无需阅读说明，可在 5 分钟内完成一次标准深度生成；
- 任一生成结果均可追溯到输入、深度策略、模型、节点和版本。

### 3.11 关键假设与风险

| 假设 / 风险 | 影响 | 应对方式 |
| --- | --- | --- |
| 用户愿意回答澄清问题 | 问题过多会造成流失 | 按深度限制数量；问题必须说明影响；允许“使用建议值” |
| 结构化输出在不同模型上表现不一 | 解析失败或字段缺失 | Pydantic 校验、JSON 修复、有限重试、失败降级为草稿 |
| Tauri 打包 Python sidecar 较复杂 | 跨平台构建耗时 | 首版只保证 Windows；CI 与其他平台打包列为后续任务 |
| 本地 API Key 可能泄露 | 安全风险 | 使用系统凭据存储；日志脱敏；禁止写入 SQLite 和导出文件 |
| “Bubble”名称与 Bubble.io 冲突 | 搜索、品牌和简历表达受影响 | 发布前完成命名检索并更名；当前仅作为内部代号 |
| 为展示前沿技术而过度设计 | 无法按期完成 | 每个框架必须对应一个可演示问题；P1 不影响 P0 闭环 |

### 3.12 待确认问题

- 最终公开名称与视觉识别；
- 是否只提供 Windows 安装包，还是同时提供 macOS 构建说明；
- 首个默认模型选择 DeepSeek 还是通义千问；
- 深入模式的 API 草案是否需要导出为 OpenAPI YAML。

这些问题不阻塞 MVP 开发，可在第 4 周前决定。

## 4. 技术方案

### 4.1 技术栈

| 层级 | 建议技术 | 选择原因 / 面试价值 |
| --- | --- | --- |
| 桌面外壳 | Tauri 2 | 安装包轻量；可嵌入外部二进制；适合演示桌面进程、权限和 sidecar 生命周期管理 |
| 前端 | React + TypeScript + Vite | 快速完成 Bubble 列表、工作台、产物预览和运行轨迹；生态成熟 |
| UI | Tailwind CSS + 少量 Headless 组件 | 降低设计成本，避免重型 UI 框架影响作品辨识度 |
| Python 服务 | FastAPI + Uvicorn | 异步接口、依赖注入、Pydantic 集成和自动 OpenAPI，适合后端岗位展示 |
| 流式通信 | SSE | Agent 输出以服务端单向推送为主；实现与重连语义比 WebSocket 更简单 |
| Agent 编排 | LangGraph `StateGraph` | 条件路由、持久化、interrupt、恢复执行和流式事件与项目需求直接对应 |
| 模型接入 | LangChain 模型适配层 + OpenAI-compatible 客户端 | 首版统一接入 DeepSeek、通义千问和兼容服务，避免在业务节点内耦合供应商 SDK |
| Schema | Pydantic v2 | 定义图状态和产物契约，负责校验、重试条件和 API Schema |
| 业务存储 | SQLite + SQLAlchemy 2 + Alembic | 本地优先、零运维；仍可展示 Repository、事务与迁移设计 |
| 图检查点 | LangGraph SQLite checkpointer | 保存 thread 状态，支持中断、恢复、失败重试和时间旅行调试 |
| 凭据 | 操作系统凭据库（Python `keyring` 或 Tauri 安全存储） | API Key 不进入数据库、日志和 Git |
| 可观测性 | 本地 RunEvent + 可选 LangSmith | 离线也能演示执行轨迹；联网时可展示 Trace 与评测能力 |
| 工程质量 | pytest、pytest-asyncio、respx、Ruff、mypy | 覆盖图路由、API、模型失败和结构化输出边界 |
| 打包 | PyInstaller Python sidecar + Tauri bundler | Tauri 官方支持将 Python CLI/API 服务作为 external binary 打包 |

LangGraph 的官方定位正是长时间运行、有状态 Agent 的低层编排运行时，核心能力包括 durable execution、streaming、human-in-the-loop 与 persistence，和本项目的问题高度匹配。参考：[LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)、[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)。Tauri 的 sidecar 机制也明确支持将 Python CLI 或 API 服务通过 PyInstaller 打包，参考：[Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)。

### 4.2 进程与通信约束

- Tauri 启动时拉起 FastAPI sidecar，退出时负责终止子进程；
- 后端仅绑定 `127.0.0.1`，使用随机可用端口；
- Tauri 为每次启动生成临时访问令牌，前端请求必须携带该令牌；
- 普通 CRUD 使用 HTTP JSON，运行事件使用 SSE；
- Sidecar 健康检查通过后再开放工作台；异常退出时给出重启入口；
- API Key 只在模型调用边界读取，任何日志对象先经过脱敏过滤。

## 5. LangGraph 工作流设计

### 5.1 核心状态

建议使用一个可序列化的 `ProjectGraphState`，至少包含：

- `bubble_id`、`run_id`、`thread_id`；
- `raw_idea`、`depth`、`depth_policy`；
- `known_facts`、`assumptions`、`constraints`；
- `clarifying_questions`、`user_answers`、`confirmed_scope`；
- `candidate_directions`、`selected_direction`；
- `artifacts`、`review_issues`、`revision_count`；
- `current_stage`、`errors`、`model_usage`。

状态只存结构化数据；展示用 Markdown 由 Artifact Renderer 生成，避免把长文本当作系统的唯一事实来源。

### 5.2 节点职责

1. `normalize_idea`：提取用户、问题、目标与显式约束。
2. `route_by_depth`：加载 `DepthPolicy`，决定后续分支和预算。
3. `find_information_gaps`：只生成会实质影响方案的问题。
4. `await_user_confirmation`：通过 LangGraph interrupt 暂停，等待用户回答并确认边界。
5. `diverge_directions`：标准/深入模式生成 2–3 个不同方向。
6. `score_and_converge`：按价值、工作量、风险和约束匹配度选择方向，并保留选择理由。
7. `define_mvp`：生成必须做、可选和明确不做的范围。
8. `recommend_stack`：从受控技术目录读取候选，再由模型结合约束说明取舍。
9. `draft_artifacts`：根据深度生成对应 Pydantic Artifact。
10. `critic_review`：检查范围回流、术语矛盾、不可验证指标和技术冲突。
11. `revise_artifacts`：只修复 Critic 指出的字段；超过深度规定轮次则停止。
12. `persist_and_render`：原子保存结构化产物、Markdown 版本和 RunEvent。

### 5.3 条件路由

- 信息足够则跳过多余问题；信息不足则进入人工确认点；
- 轻量模式跳过发散和 LLM Critic，只运行确定性规则校验；
- 标准模式运行一次 Critic；深入模式最多运行两次；
- Schema 校验失败时进入定向修复，最多重试两次；
- 用户取消、模型超时或预算耗尽时保存检查点，并返回可恢复状态；
- Critic 没有高优先级问题时直接持久化，避免无意义循环。

### 5.4 可靠性设计

- 每次运行生成唯一 `run_id`，每个节点写入幂等事件；
- Artifact 使用 `(bubble_id, artifact_type, version)` 唯一约束；
- 节点先产出状态更新，持久化节点再用事务提交业务数据；
- 只对超时、限流和临时网络错误执行指数退避；认证失败不重试；
- Prompt、模型配置和 Schema 都记录版本号，保证结果可复现；
- 设置单次运行 Token 与费用预算，超过预算在安全检查点停止；
- 流式输出是展示通道，不作为最终存储事实，最终以校验后的 Artifact 为准。

## 6. 数据与 API 设计

### 6.1 核心实体

| 实体 | 关键字段 | 用途 |
| --- | --- | --- |
| `Bubble` | id、name、raw_idea、depth、status、created_at、updated_at | 项目容器 |
| `Message` | id、bubble_id、role、content、created_at | 保存用户与 Agent 对话 |
| `Decision` | id、bubble_id、key、value、source、confirmed_at | 保存假设、约束和用户确认 |
| `Artifact` | id、bubble_id、type、schema_json、markdown、version | 保存结构化产物及渲染结果 |
| `AgentRun` | id、bubble_id、thread_id、status、model、prompt_version、usage | 一次图执行记录 |
| `RunEvent` | id、run_id、node、event_type、payload、duration_ms | 本地执行轨迹与调试数据 |
| `ModelProfile` | id、provider、model_name、base_url、credential_ref | 模型配置；只保存凭据引用 |

LangGraph 自身的 checkpoint 表与业务表分开管理。业务层不直接依赖 checkpoint 内部结构，以便未来更换持久化实现。

### 6.2 MVP API

| 方法与路径 | 用途 |
| --- | --- |
| `POST /api/bubbles` | 新建 Bubble |
| `GET /api/bubbles` | 获取 Bubble 列表 |
| `GET /api/bubbles/{id}` | 获取工作台数据与最新产物 |
| `PATCH /api/bubbles/{id}` | 重命名或更新深度 |
| `DELETE /api/bubbles/{id}` | 删除前二次确认 |
| `POST /api/bubbles/{id}/runs` | 启动一次生成或修订 |
| `GET /api/runs/{id}` | 获取运行状态 |
| `GET /api/runs/{id}/events` | 通过 SSE 获取节点与文本事件 |
| `POST /api/runs/{id}/resume` | 提交人工回答并从 interrupt 恢复 |
| `POST /api/runs/{id}/cancel` | 请求在安全点取消 |
| `GET /api/bubbles/{id}/artifacts/{type}` | 获取某类产物及版本 |
| `GET /api/bubbles/{id}/export` | 导出 Markdown 文档包 |
| `POST /api/model-profiles/test` | 测试模型配置，不记录密钥 |

## 7. Agent 评测方案

评测不是附加项，而是该项目区别于普通 LLM Demo 的关键。

### 7.1 固定测试集

准备 20 个覆盖不同领域和完整度的想法，例如待办工具、校园二手平台、AI 面试教练、IoT 仪表盘和纯后端 API。每个样本标注：

- 必须追问的信息；
- 不应自行假设的内容；
- 合理的 MVP 功能上限；
- 明确禁止或超出范围的功能；
- 三种深度应出现的产物类型。

### 7.2 自动指标

- Schema 有效率；
- 必填字段覆盖率；
- 深度策略遵从率；
- “本版不做”回流率；
- PRD、MVP、技术栈之间的术语一致率；
- 平均模型调用次数、延迟与 Token；
- 中断恢复与失败恢复成功率。

### 7.3 测试分层

- 单元测试：深度路由、校验器、Renderer、重试策略；
- 图测试：使用 Fake LLM 验证节点顺序、interrupt 与条件边；
- API 测试：异步运行、SSE 重连、取消与错误码；
- 集成测试：SQLite checkpoint 后重启进程并恢复；
- 模型评测：对固定测试集运行真实模型，保存结果但不纳入默认 CI。

## 8. 项目目录建议

```text
bubble-agent/
├─ apps/
│  └─ desktop/                 # React + Tauri
├─ backend/
│  ├─ app/
│  │  ├─ api/                  # FastAPI routers
│  │  ├─ agents/               # LangGraph nodes, edges, policies
│  │  ├─ artifacts/            # Pydantic schemas and renderers
│  │  ├─ models/               # LLM provider adapters
│  │  ├─ persistence/          # SQLAlchemy repositories/checkpointer setup
│  │  ├─ observability/        # events, metrics, redaction
│  │  └─ main.py
│  ├─ tests/
│  └─ pyproject.toml
├─ evals/
│  ├─ datasets/
│  └─ runners/
├─ docs/
└─ README.md
```

## 9. 4–6 周开发计划

| 周次 | 目标 | 可验收结果 |
| --- | --- | --- |
| 第 1 周 | 工程骨架与契约 | Tauri 能启动/关闭 FastAPI；完成数据库迁移、健康检查和核心 Pydantic Schema |
| 第 2 周 | Bubble 与流式后端 | CRUD、SSE、RunEvent、模型适配器和 API Key 安全存储可用 |
| 第 3 周 | LangGraph 主链路 | 三档路由、澄清 interrupt、生成、Critic、重试和 SQLite checkpoint 跑通 |
| 第 4 周 | 桌面工作台 | 完成 Bubble 列表、创建流程、对话、产物 Tab 和轨迹面板，形成 P0 Demo |
| 第 5 周 | 测试与评测 | 固定测试集、图测试、恢复测试、错误处理和性能数据完成 |
| 第 6 周 | 面试包装 | Windows 安装包、README、演示视频、技术复盘、可选 LangSmith Trace 完成 |

若只有 4 周：合并第 1–2 周，取消 P1、跨平台打包、版本差异和 LangSmith，仅保留本地 RunEvent。

## 10. 面试展示设计

### 10.1 60 秒项目介绍

“Bubble Agent 是一个本地桌面端的项目规划 Agent。它与普通 PRD 生成器最大的区别是，开发深度不是 Prompt 参数，而是 LangGraph 的执行策略：不同深度会改变澄清次数、图分支、产物 Schema 和评审轮次。系统在生成前通过 interrupt 让用户确认范围，用 Pydantic 保证结构化输出，用 SQLite checkpoint 支持崩溃恢复，并记录每个节点的耗时、重试和版本。后端采用 FastAPI 和 SSE，桌面端通过 Tauri 打包 Python sidecar。”

### 10.2 推荐演示流程

1. 输入一个故意模糊的想法，选择标准深度；
2. 展示 Agent 只追问影响方案的关键问题；
3. 在人工确认点关闭并重启应用，再继续执行；
4. 展示 PRD、MVP 与技术栈的结构化产物；
5. 打开轨迹面板解释深度路由、Critic 修订和 Token 使用；
6. 切换轻量深度，对比节点数量与产物差异；
7. 导出 Markdown，说明如何交给后续编码 Agent。

### 10.3 可重点讨论的面试题

- 为什么使用 LangGraph，而不是一条 LangChain Chain 或手写 `if/else`；
- 为什么 SSE 比 WebSocket 更适合当前事件流；
- Checkpoint 与业务数据库为什么分离；
- 如何保证重复恢复不会重复写 Artifact；
- 如何处理模型 JSON 不合法、超时、限流和认证失败；
- 如何避免 Critic 无限自我修改；
- 如何衡量一个 PRD Agent 是否真的变好；
- 本地 sidecar 的端口、鉴权、进程回收和密钥安全问题。

## 11. MVP 完成定义

项目只有同时满足以下条件才算完成：

- Windows 上能以桌面应用形式启动，用户无需手动启动 Python 服务；
- 三种深度至少各有一个端到端自动化测试；
- 用户确认前不会生成最终方案；
- 标准模式能生成并保存 PRD、MVP 和技术栈；
- 应用重启后能恢复一个被 interrupt 或临时错误暂停的运行；
- 用户能看到节点级运行轨迹并导出 Markdown；
- API Key 不出现在数据库、日志、Trace 或导出文件；
- README 包含架构取舍、运行方式、测试方式、演示 GIF/视频和已知限制；
- 仓库中至少包含 20 个 Agent 评测样本及一份结果报告。

## 12. 参考资料

- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [Tauri：Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Ideate GitHub](https://github.com/kevinelliott/ideate)
- [Ombuto Code GitHub](https://github.com/FrancoisBotha/ombutocode)
- [Norvo](https://norvo.pro/)
- [IdeaPico](https://ideapico.com/)
- [Specd](https://specd.app/how-it-works)
- [ChatPRD](https://www.chatprd.ai/product/features/write-prd)
- [Dyad](https://www.dyad.sh/)
- [Bubble AI](https://bubble.io/ai)
