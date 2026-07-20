import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, subscribeToRun } from "./api";
import type {
  AgentRun,
  Artifact,
  Bubble,
  BubbleDetail,
  ClarifyingQuestion,
  Depth,
  Health,
  RunEvent,
} from "./types";

const depthMeta: Record<Depth, { label: string; code: string; note: string; output: string }> = {
  spark: {
    label: "轻量",
    code: "SPARK",
    note: "快速验证方向",
    output: "摘要 · MVP",
  },
  builder: {
    label: "标准",
    code: "BUILDER",
    note: "适合个人开发",
    output: "PRD · 用户故事 · 技术栈",
  },
  architect: {
    label: "深入",
    code: "ARCHITECT",
    note: "完整技术规划",
    output: "数据实体 · API · 测试策略",
  },
};

const statusLabel: Record<string, string> = {
  draft: "草稿",
  queued: "排队中",
  running: "生成中",
  waiting: "等你确认",
  ready: "已完成",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const nodeLabel: Record<string, string> = {
  orchestrator: "运行调度",
  normalize_idea: "整理原始想法",
  route_by_depth: "加载深度策略",
  find_information_gaps: "识别信息缺口",
  await_user_confirmation: "等待范围确认",
  diverge_directions: "发散项目方向",
  score_and_converge: "评分并收敛",
  define_mvp: "定义 MVP",
  recommend_stack: "选择技术栈",
  draft_artifacts: "生成结构化产物",
  critic_review: "Critic 一致性评审",
  revise_artifacts: "定向修订",
  persist_and_render: "保存并渲染",
};

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BubbleDetail | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [creating, setCreating] = useState(true);
  const [activeArtifact, setActiveArtifact] = useState<string>("prd");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBubbles = useCallback(async () => {
    const items = await api.listBubbles();
    setBubbles(items);
    return items;
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    const next = await api.getBubble(id);
    setDetail(next);
    if (next.artifacts.length > 0) {
      setActiveArtifact((current) =>
        next.artifacts.some((item) => item.artifact_type === current)
          ? current
          : next.artifacts[0].artifact_type,
      );
    }
    if (next.latest_run) {
      setEvents(await api.events(next.latest_run.id));
    } else {
      setEvents([]);
    }
    return next;
  }, []);

  useEffect(() => {
    Promise.all([api.health(), loadBubbles()])
      .then(([system, items]) => {
        setHealth(system);
        if (items.length > 0) {
          setSelectedId(items[0].id);
          setCreating(false);
        }
      })
      .catch((cause: unknown) => setError(messageOf(cause)));
  }, [loadBubbles]);

  useEffect(() => {
    if (!selectedId || creating) return;
    loadDetail(selectedId).catch((cause: unknown) => setError(messageOf(cause)));
  }, [creating, loadDetail, selectedId]);

  const latestRun = detail?.latest_run ?? null;
  useEffect(() => {
    if (!latestRun || !["queued", "running"].includes(latestRun.status)) return;
    const afterId = events.at(-1)?.id ?? 0;
    let unsubscribe: (() => void) | undefined;
    void subscribeToRun(
      latestRun.id,
      afterId,
      (event) => {
        setEvents((current) =>
          current.some((item) => item.id === event.id) ? current : [...current, event],
        );
      },
      (run) => {
        setDetail((current) => (current ? { ...current, latest_run: run } : current));
        if (selectedId) {
          Promise.all([loadDetail(selectedId), loadBubbles()]).catch((cause: unknown) =>
            setError(messageOf(cause)),
          );
        }
      },
      () => {
        if (selectedId) {
          window.setTimeout(() => {
            loadDetail(selectedId).catch((cause: unknown) => setError(messageOf(cause)));
          }, 500);
        }
      },
    ).then((cleanup) => {
      unsubscribe = cleanup;
    });
    return () => unsubscribe?.();
  }, [events, latestRun, loadBubbles, loadDetail, selectedId]);

  const selectBubble = (id: string) => {
    setSelectedId(id);
    setCreating(false);
    setError(null);
  };

  const createProject = async (payload: { name: string; raw_idea: string; depth: Depth }) => {
    setBusy(true);
    setError(null);
    try {
      const bubble = await api.createBubble(payload);
      const run = await api.startRun(bubble.id);
      setSelectedId(bubble.id);
      setCreating(false);
      setDetail({ bubble: { ...bubble, status: "running" }, artifacts: [], latest_run: run });
      setEvents([]);
      await loadBubbles();
    } catch (cause: unknown) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  };

  const confirmScope = async (answers: Record<string, string>) => {
    if (!latestRun) return;
    setBusy(true);
    setError(null);
    try {
      const run = await api.resumeRun(latestRun.id, answers);
      setDetail((current) => (current ? { ...current, latest_run: run } : current));
      if (selectedId) await loadDetail(selectedId);
    } catch (cause: unknown) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  };

  const rerun = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      const run = await api.startRun(selectedId, "基于当前 Bubble 重新检查并生成新版本");
      setDetail((current) => (current ? { ...current, latest_run: run } : current));
      setEvents([]);
    } catch (cause: unknown) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  };

  const removeCurrent = async () => {
    if (!selectedId || !detail) return;
    if (!window.confirm(`确定删除“${detail.bubble.name}”及其所有本地记录吗？`)) return;
    await api.deleteBubble(selectedId);
    const items = await loadBubbles();
    setDetail(null);
    setEvents([]);
    if (items.length > 0) {
      setSelectedId(items[0].id);
      setCreating(false);
    } else {
      setSelectedId(null);
      setCreating(true);
    }
  };

  const exportCurrent = async () => {
    if (!detail) return;
    try {
      const content = await api.exportBubble(detail.bubble.id);
      const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${detail.bubble.name.replace(/[^\p{L}\p{N}_-]+/gu, "-") || "bubble"}.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause: unknown) {
      setError(messageOf(cause));
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        bubbles={bubbles}
        selectedId={selectedId}
        health={health}
        creating={creating}
        onCreate={() => setCreating(true)}
        onSelect={selectBubble}
      />

      <main className="main-panel">
        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)} aria-label="关闭错误提示">
              ×
            </button>
          </div>
        )}
        {creating ? (
          <CreateBubble onSubmit={createProject} busy={busy} />
        ) : detail ? (
          <Workspace
            detail={detail}
            events={events}
            activeArtifact={activeArtifact}
            busy={busy}
            onArtifactChange={setActiveArtifact}
            onConfirm={confirmScope}
            onRerun={rerun}
            onDelete={removeCurrent}
            onExport={exportCurrent}
          />
        ) : (
          <LoadingState />
        )}
      </main>
    </div>
  );
}

function Sidebar({
  bubbles,
  selectedId,
  health,
  creating,
  onCreate,
  onSelect,
}: {
  bubbles: Bubble[];
  selectedId: string | null;
  health: Health | null;
  creating: boolean;
  onCreate: () => void;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="sidebar">
      <div className="brand-row">
        <div className="brand-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div>
          <strong>bubble</strong>
          <small>PROJECT AGENT</small>
        </div>
      </div>

      <button className="new-bubble" onClick={onCreate}>
        <span>＋</span> 新建 Bubble
      </button>

      <div className="side-heading">
        <span>PROJECT MEMORY</span>
        <span>{String(bubbles.length).padStart(2, "0")}</span>
      </div>
      <nav className="bubble-list" aria-label="Bubble 列表">
        {bubbles.map((bubble) => (
          <button
            key={bubble.id}
            className={`bubble-item ${selectedId === bubble.id && !creating ? "active" : ""}`}
            onClick={() => onSelect(bubble.id)}
          >
            <span className={`status-orb ${bubble.status}`} />
            <span className="bubble-item-copy">
              <strong>{bubble.name}</strong>
              <small>{depthMeta[bubble.depth].label} · {statusLabel[bubble.status]}</small>
            </span>
            <span className="chevron">›</span>
          </button>
        ))}
        {bubbles.length === 0 && <p className="empty-list">还没有 Bubble。<br />从一个想法开始。</p>}
      </nav>

      <div className="system-card">
        <div className="system-status">
          <span className={health ? "online" : "offline"} />
          {health ? "本地 Agent 在线" : "等待后端连接"}
        </div>
        <p>{health ? `${health.provider} / ${health.model}` : "127.0.0.1:8765"}</p>
      </div>
    </aside>
  );
}

function CreateBubble({
  onSubmit,
  busy,
}: {
  onSubmit: (payload: { name: string; raw_idea: string; depth: Depth }) => Promise<void>;
  busy: boolean;
}) {
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [depth, setDepth] = useState<Depth>("builder");
  const valid = name.trim().length > 0 && idea.trim().length >= 10;

  return (
    <section className="create-screen">
      <div className="ambient-bubble bubble-a" />
      <div className="ambient-bubble bubble-b" />
      <div className="create-content">
        <div className="eyebrow"><span>01</span> CAPTURE THE THOUGHT</div>
        <h1>先别急着写代码。<br />把想法放进一个 <em>Bubble</em>。</h1>
        <p className="create-lead">
          Agent 会先找到信息缺口，等你确认边界，再沿着真实的状态图生成方案。
        </p>

        <form
          className="idea-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (valid) void onSubmit({ name: name.trim(), raw_idea: idea.trim(), depth });
          }}
        >
          <label>
            <span>项目名称</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：校园面试教练"
              maxLength={80}
            />
          </label>
          <label>
            <span>你的原始想法</span>
            <textarea
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder="哪怕只有一句话也可以。说清楚你想做什么，以及为什么想做……"
              rows={5}
              maxLength={5000}
            />
            <small>{idea.length} / 5000</small>
          </label>

          <fieldset>
            <legend><span>02</span> 选择开发深度</legend>
            <div className="depth-grid">
              {(Object.keys(depthMeta) as Depth[]).map((key) => (
                <button
                  type="button"
                  key={key}
                  className={`depth-card ${depth === key ? "selected" : ""}`}
                  onClick={() => setDepth(key)}
                >
                  <span className="depth-code">{depthMeta[key].code}</span>
                  <strong>{depthMeta[key].label}</strong>
                  <p>{depthMeta[key].note}</p>
                  <small>{depthMeta[key].output}</small>
                </button>
              ))}
            </div>
          </fieldset>

          <button className="primary-action" type="submit" disabled={!valid || busy}>
            {busy ? "正在创建状态图…" : "开始梳理想法"}
            <span>↗</span>
          </button>
        </form>
      </div>
    </section>
  );
}

function Workspace({
  detail,
  events,
  activeArtifact,
  busy,
  onArtifactChange,
  onConfirm,
  onRerun,
  onDelete,
  onExport,
}: {
  detail: BubbleDetail;
  events: RunEvent[];
  activeArtifact: string;
  busy: boolean;
  onArtifactChange: (type: string) => void;
  onConfirm: (answers: Record<string, string>) => Promise<void>;
  onRerun: () => Promise<void>;
  onDelete: () => Promise<void>;
  onExport: () => Promise<void>;
}) {
  const run = detail.latest_run;
  const waiting = run?.status === "waiting" && run.interrupt_payload;
  const active = detail.artifacts.find((item) => item.artifact_type === activeArtifact);

  return (
    <div className="workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow"><span>PROJECT</span> {depthMeta[detail.bubble.depth].code}</div>
          <h2>{detail.bubble.name}</h2>
          <p>{detail.bubble.raw_idea}</p>
        </div>
        <div className="workspace-actions">
          <span className={`run-chip ${run?.status ?? detail.bubble.status}`}>
            <i /> {statusLabel[run?.status ?? detail.bubble.status]}
          </span>
          {detail.artifacts.length > 0 && (
            <button className="icon-button" onClick={() => void onExport()} title="导出 Markdown">
              ⇩
            </button>
          )}
          <button className="icon-button" onClick={() => void onRerun()} title="生成新版本" disabled={busy}>
            ↻
          </button>
          <button className="icon-button danger" onClick={() => void onDelete()} title="删除 Bubble">
            ×
          </button>
        </div>
      </header>

      <div className="workspace-body">
        <section className="artifact-column">
          {waiting ? (
            <ConfirmationPanel
              key={run.id}
              questions={run.interrupt_payload!.questions}
              knownFacts={run.interrupt_payload!.known_facts}
              assumptions={run.interrupt_payload!.assumptions}
              busy={busy}
              onConfirm={onConfirm}
            />
          ) : detail.artifacts.length > 0 ? (
            <>
              <div className="artifact-tabs">
                {detail.artifacts.map((artifact) => (
                  <button
                    key={artifact.artifact_type}
                    className={activeArtifact === artifact.artifact_type ? "active" : ""}
                    onClick={() => onArtifactChange(artifact.artifact_type)}
                  >
                    {artifactLabel(artifact)}
                    <small>v{artifact.version}</small>
                  </button>
                ))}
              </div>
              {active && (
                <article className="markdown-document">
                  <div className="document-meta">
                    <span>STRUCTURED ARTIFACT</span>
                    <span>{new Date(active.created_at).toLocaleString("zh-CN")}</span>
                  </div>
                  <ReactMarkdown>{active.markdown}</ReactMarkdown>
                </article>
              )}
            </>
          ) : (
            <RunningCanvas run={run} events={events} />
          )}
        </section>
        <TracePanel run={run} events={events} />
      </div>
    </div>
  );
}

function ConfirmationPanel({
  questions,
  knownFacts,
  assumptions,
  busy,
  onConfirm,
}: {
  questions: ClarifyingQuestion[];
  knownFacts: string[];
  assumptions: string[];
  busy: boolean;
  onConfirm: (answers: Record<string, string>) => Promise<void>;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((item) => [item.id, item.suggested_answer ?? ""])),
  );
  const complete = questions.every((item) => answers[item.id]?.trim());

  return (
    <div className="confirmation-card">
      <div className="confirmation-heading">
        <span className="pulse-ring"><i /></span>
        <div>
          <div className="eyebrow"><span>HUMAN IN THE LOOP</span> INTERRUPT</div>
          <h3>先确认边界，再继续生成。</h3>
          <p>这些回答会写入 Bubble 的决策记录，并从当前 checkpoint 恢复执行。</p>
        </div>
      </div>

      <div className="scope-summary">
        <div>
          <strong>已知事实</strong>
          {knownFacts.map((item) => <p key={item}>✓ {item}</p>)}
        </div>
        <div>
          <strong>待确认假设</strong>
          {assumptions.map((item) => <p key={item}>? {item}</p>)}
        </div>
      </div>

      <div className="questions">
        {questions.map((question, index) => (
          <label key={question.id}>
            <span className="question-number">Q{String(index + 1).padStart(2, "0")}</span>
            <span className="question-copy">
              <strong>{question.question}</strong>
              <small>{question.why_it_matters}</small>
              <input
                value={answers[question.id] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({ ...current, [question.id]: event.target.value }))
                }
                placeholder={question.suggested_answer ?? "输入你的答案"}
              />
            </span>
          </label>
        ))}
      </div>

      <button
        className="primary-action compact"
        disabled={!complete || busy}
        onClick={() => void onConfirm(answers)}
      >
        {busy ? "正在恢复状态图…" : "确认范围并继续"}<span>→</span>
      </button>
    </div>
  );
}

function RunningCanvas({ run, events }: { run?: AgentRun | null; events: RunEvent[] }) {
  const completedNodes = events.filter((item) => item.event_type === "node_completed").length;
  return (
    <div className="running-canvas">
      <div className="orbit"><span /><span /><span /></div>
      <div className="eyebrow"><span>LANGGRAPH</span> DURABLE RUN</div>
      <h3>{run?.current_node ? nodeLabel[run.current_node] ?? run.current_node : "正在准备工作流"}</h3>
      <p>Agent 正在按开发深度执行。所有节点变化都会写入本地运行轨迹。</p>
      <div className="progress-rule"><span style={{ width: `${Math.min(92, completedNodes * 10 + 8)}%` }} /></div>
      <small>{completedNodes} 个节点已完成</small>
    </div>
  );
}

function TracePanel({ run, events }: { run?: AgentRun | null; events: RunEvent[] }) {
  const nodeEvents = useMemo(
    () => events.filter((item) => ["node_completed", "node_failed", "human_input_required"].includes(item.event_type)),
    [events],
  );
  const totalDuration = nodeEvents.reduce((sum, item) => sum + (item.duration_ms ?? 0), 0);

  return (
    <aside className="trace-panel">
      <div className="trace-heading">
        <div>
          <div className="eyebrow"><span>LIVE</span> EXECUTION TRACE</div>
          <h3>Agent 运行轨迹</h3>
        </div>
        <span className="event-count">{events.length}</span>
      </div>
      <div className="trace-metrics">
        <div><small>MODEL</small><strong>{run?.model_name ?? "—"}</strong></div>
        <div><small>NODE TIME</small><strong>{totalDuration}ms</strong></div>
      </div>
      <div className="timeline">
        {nodeEvents.map((event) => (
          <div className={`timeline-item ${event.event_type}`} key={event.id}>
            <span className="timeline-dot" />
            <div>
              <strong>{nodeLabel[event.node] ?? event.node}</strong>
              <p>{eventText(event)}</p>
              <small>
                {new Date(event.created_at).toLocaleTimeString("zh-CN", { hour12: false })}
                {event.duration_ms != null ? ` · ${event.duration_ms}ms` : ""}
              </small>
            </div>
          </div>
        ))}
        {nodeEvents.length === 0 && <p className="empty-trace">工作流启动后，节点会出现在这里。</p>}
      </div>
      <div className="trace-footer">
        <span>THREAD</span>
        <code>{run?.thread_id?.slice(0, 13) ?? "not-started"}</code>
      </div>
    </aside>
  );
}

function LoadingState() {
  return <div className="loading-state"><span /><p>正在读取本地 Bubble…</p></div>;
}

function artifactLabel(artifact: Artifact): string {
  const labels: Record<string, string> = {
    prd: "产品定义",
    mvp: "MVP 范围",
    technical_plan: "技术方案",
    architecture_draft: "深入设计",
  };
  return labels[artifact.artifact_type] ?? artifact.artifact_type;
}

function eventText(event: RunEvent): string {
  if (event.event_type === "human_input_required") return "图已持久化，等待用户确认";
  if (event.event_type === "node_failed") return String(event.payload.message ?? "节点执行失败");
  const fields = event.payload.updated_fields;
  return Array.isArray(fields) && fields.length > 0 ? `更新：${fields.join(" / ")}` : "节点执行完成";
}

function messageOf(cause: unknown): string {
  return cause instanceof Error ? cause.message : "发生未知错误";
}

export default App;
