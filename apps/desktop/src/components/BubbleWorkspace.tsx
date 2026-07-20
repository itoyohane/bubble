"use client";

import {
  ArrowClockwise,
  ArrowUpRight,
  Atom,
  Buildings,
  ChatCircleDots,
  CheckCircle,
  CircleNotch,
  DownloadSimple,
  FileText,
  FlowArrow,
  FolderOpen,
  GearSix,
  PaperPlaneTilt,
  Plus,
  Sparkle,
  Stack,
  Trash,
  Warning,
  X,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, subscribeToRun } from "@/src/api";
import type {
  AgentRun,
  Artifact,
  Bubble,
  BubbleDetail,
  ClarifyingQuestion,
  Depth,
  Health,
  RunEvent,
} from "@/src/types";

const depthMeta: Record<Depth, { label: string; code: string; note: string; size: number }> = {
  spark: { label: "轻量", code: "SPARK", note: "快速验证", size: 116 },
  builder: { label: "标准", code: "BUILDER", note: "完整 MVP", size: 158 },
  architect: { label: "深入", code: "ARCHITECT", note: "系统设计", size: 202 },
};

const statusLabel: Record<string, string> = {
  draft: "草稿",
  queued: "排队中",
  running: "生成中",
  waiting: "待确认",
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
  critic_review: "一致性评审",
  revise_artifacts: "定向修订",
  persist_and_render: "保存并渲染",
};

type ComposerPoint = { x: number; y: number };
type BubbleOrigins = Record<string, { xRatio: number; yRatio: number }>;

const ORIGIN_KEY = "bubble-agent:canvas-origins";

export function BubbleWorkspace() {
  const canvasRef = useRef<HTMLElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const [canvasSize, setCanvasSize] = useState({ width: 960, height: 720 });
  const [health, setHealth] = useState<Health | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [origins, setOrigins] = useState<BubbleOrigins>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BubbleDetail | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [composerPoint, setComposerPoint] = useState<ComposerPoint | null>(null);
  const [activeArtifact, setActiveArtifact] = useState("prd");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBubbles = useCallback(async () => {
    const items = await api.listBubbles();
    setBubbles(items);
    return items;
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    const next = await api.getBubble(id);
    setDetail(next);
    if (next.artifacts.length) {
      setActiveArtifact((current) =>
        next.artifacts.some((item) => item.artifact_type === current)
          ? current
          : next.artifacts[0].artifact_type,
      );
    }
    setEvents(next.latest_run ? await api.events(next.latest_run.id) : []);
    return next;
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem(ORIGIN_KEY);
    if (stored) {
      try {
        setOrigins(JSON.parse(stored) as BubbleOrigins);
      } catch {
        window.localStorage.removeItem(ORIGIN_KEY);
      }
    }
    Promise.all([api.health(), loadBubbles()])
      .then(([system, items]) => {
        setHealth(system);
        if (items[0]) setSelectedId(items[0].id);
      })
      .catch((cause: unknown) => setError(messageOf(cause)))
      .finally(() => setLoading(false));
  }, [loadBubbles]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const observer = new ResizeObserver(([entry]) => {
      setCanvasSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    loadDetail(selectedId).catch((cause: unknown) => setError(messageOf(cause)));
  }, [loadDetail, selectedId]);

  useEffect(() => {
    if (!bubbles.some((bubble) => ["draft", "running", "waiting"].includes(bubble.status))) return;
    const timer = window.setInterval(() => {
      loadBubbles().catch((cause: unknown) => setError(messageOf(cause)));
    }, 1800);
    return () => window.clearInterval(timer);
  }, [bubbles, loadBubbles]);

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
      () => {
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

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (composerPoint) setComposerPoint(null);
      else if (drawerOpen) setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [composerPoint, drawerOpen]);

  const selectedBubble = bubbles.find((bubble) => bubble.id === selectedId) ?? null;
  const completed = useMemo(
    () => bubbles.filter((bubble) => bubble.status === "ready").sort(byUpdated),
    [bubbles],
  );
  const unfinished = useMemo(
    () => bubbles.filter((bubble) => bubble.status !== "ready").sort(byUpdated),
    [bubbles],
  );

  const openComposer = useCallback((point?: ComposerPoint) => {
    const fallback = { x: canvasSize.width / 2, y: canvasSize.height / 2 };
    setDrawerOpen(false);
    setComposerPoint(point ?? fallback);
    setError(null);
  }, [canvasSize]);

  const onCanvasDoubleClick = (event: React.MouseEvent<HTMLElement>) => {
    if ((event.target as HTMLElement).closest("[data-interactive]")) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    openComposer({
      x: clamp(event.clientX - bounds.left, 230, Math.max(230, bounds.width - 230)),
      y: clamp(event.clientY - bounds.top, 150, Math.max(150, bounds.height - 150)),
    });
  };

  const createProject = async (idea: string, depth: Depth, point: ComposerPoint) => {
    setBusy(true);
    setError(null);
    try {
      const bubble = await api.createBubble({
        name: projectNameFrom(idea),
        raw_idea: idea,
        depth,
      });
      const nextOrigins = {
        ...origins,
        [bubble.id]: {
          xRatio: clamp(point.x / canvasSize.width, 0.08, 0.92),
          yRatio: clamp(point.y / canvasSize.height, 0.08, 0.92),
        },
      };
      setOrigins(nextOrigins);
      window.localStorage.setItem(ORIGIN_KEY, JSON.stringify(nextOrigins));
      setBubbles((current) => [{ ...bubble, status: "running" }, ...current]);
      setSelectedId(bubble.id);
      setComposerPoint(null);
      const run = await api.startRun(bubble.id);
      setDetail({ bubble: { ...bubble, status: "running" }, artifacts: [], latest_run: run });
      setEvents([]);
      await loadBubbles();
    } catch (cause: unknown) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  };

  const selectBubble = (id: string) => {
    setSelectedId(id);
    setComposerPoint(null);
    setDrawerOpen(true);
    setError(null);
  };

  const confirmScope = async (answers: Record<string, string>) => {
    if (!latestRun) return;
    setBusy(true);
    try {
      const run = await api.resumeRun(latestRun.id, answers);
      setDetail((current) => (current ? { ...current, latest_run: run } : current));
      if (selectedId) await loadDetail(selectedId);
      await loadBubbles();
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
      await loadBubbles();
    } catch (cause: unknown) {
      setError(messageOf(cause));
    } finally {
      setBusy(false);
    }
  };

  const removeCurrent = async () => {
    if (!selectedId || !selectedBubble) return;
    if (!window.confirm(`确定删除“${selectedBubble.name}”及其全部本地记录吗？`)) return;
    try {
      await api.deleteBubble(selectedId);
      const items = await loadBubbles();
      setSelectedId(items[0]?.id ?? null);
      setDrawerOpen(false);
      setDetail(null);
      setEvents([]);
    } catch (cause: unknown) {
      setError(messageOf(cause));
    }
  };

  const exportCurrent = async () => {
    if (!selectedBubble) return;
    try {
      const content = await api.exportBubble(selectedBubble.id);
      const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${selectedBubble.name.replace(/[^\p{L}\p{N}_-]+/gu, "-") || "bubble"}.md`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause: unknown) {
      setError(messageOf(cause));
    }
  };

  const openArtifact = (type: string) => {
    setActiveArtifact(type);
    setDrawerOpen(true);
  };

  return (
    <div className="app-shell">
      <Sidebar
        bubbles={bubbles}
        selected={selectedBubble}
        detail={detail}
        health={health}
        activeArtifact={activeArtifact}
        busy={busy}
        onCreate={() => openComposer()}
        onSelect={selectBubble}
        onArtifact={openArtifact}
        onTrace={() => setDrawerOpen(true)}
        onRerun={rerun}
        onExport={exportCurrent}
        onDelete={removeCurrent}
      />

      <main
        ref={canvasRef}
        className="bubble-canvas"
        onDoubleClick={onCanvasDoubleClick}
        aria-label="泡泡区，双击任意空白位置创建项目"
      >
        <div className="canvas-grid" aria-hidden="true" />
        <CanvasHeader bubbles={bubbles} onCreate={() => openComposer()} />

        {loading ? (
          <LoadingState />
        ) : bubbles.length === 0 ? (
          <EmptyState onCreate={() => openComposer()} />
        ) : (
          <div className="bubble-stage" aria-live="polite">
            {completed.map((bubble, index) => (
              <BubbleNode
                key={bubble.id}
                bubble={bubble}
                selected={selectedId === bubble.id}
                index={index}
                groupCount={completed.length}
                band="top"
                canvasSize={canvasSize}
                origin={origins[bubble.id]}
                reducedMotion={Boolean(prefersReducedMotion)}
                onSelect={selectBubble}
              />
            ))}
            {unfinished.map((bubble, index) => (
              <BubbleNode
                key={bubble.id}
                bubble={bubble}
                selected={selectedId === bubble.id}
                index={index}
                groupCount={unfinished.length}
                band="bottom"
                canvasSize={canvasSize}
                origin={origins[bubble.id]}
                reducedMotion={Boolean(prefersReducedMotion)}
                onSelect={selectBubble}
              />
            ))}
          </div>
        )}

        <div className="band-label top-label"><CheckCircle weight="fill" /> 已完成，浮到这里</div>
        <div className="band-label bottom-label"><CircleNotch /> 生成中的想法留在这里</div>

        <AnimatePresence>
          {composerPoint && (
            <IdeaComposer
              point={composerPoint}
              busy={busy}
              onClose={() => setComposerPoint(null)}
              onSubmit={createProject}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {drawerOpen && detail && (
            <ProjectDrawer
              detail={detail}
              events={events}
              activeArtifact={activeArtifact}
              busy={busy}
              onArtifact={setActiveArtifact}
              onConfirm={confirmScope}
              onClose={() => setDrawerOpen(false)}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && <ErrorToast message={error} onClose={() => setError(null)} />}
        </AnimatePresence>
      </main>
    </div>
  );
}

function Sidebar({
  bubbles,
  selected,
  detail,
  health,
  activeArtifact,
  busy,
  onCreate,
  onSelect,
  onArtifact,
  onTrace,
  onRerun,
  onExport,
  onDelete,
}: {
  bubbles: Bubble[];
  selected: Bubble | null;
  detail: BubbleDetail | null;
  health: Health | null;
  activeArtifact: string;
  busy: boolean;
  onCreate: () => void;
  onSelect: (id: string) => void;
  onArtifact: (type: string) => void;
  onTrace: () => void;
  onRerun: () => Promise<void>;
  onExport: () => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  return (
    <aside className="sidebar" data-interactive>
      <div className="brand-row">
        <span className="brand-mark"><Atom size={23} weight="duotone" /></span>
        <span><strong>bubble</strong><small>LOCAL PROJECT AGENT</small></span>
      </div>

      <button className="new-bubble" onClick={onCreate}>
        <Plus size={17} weight="bold" /> 捕获新想法
      </button>

      <SidebarSection icon={<FolderOpen />} title="空间" count={bubbles.length}>
        <nav className="project-list" aria-label="项目 Bubble 列表">
          {bubbles.map((bubble) => (
            <button
              key={bubble.id}
              className={selected?.id === bubble.id ? "active" : ""}
              onClick={() => onSelect(bubble.id)}
            >
              <span className={`status-dot ${bubble.status}`} />
              <span><strong>{bubble.name}</strong><small>{depthMeta[bubble.depth].label} · {statusLabel[bubble.status]}</small></span>
            </button>
          ))}
          {!bubbles.length && <p className="side-empty">双击右侧空白区，创建第一个 Bubble。</p>}
        </nav>
      </SidebarSection>

      <SidebarSection icon={<FileText />} title="文件" count={detail?.artifacts.length ?? 0}>
        <div className="file-list">
          {detail?.artifacts.map((artifact) => (
            <button
              key={artifact.artifact_type}
              className={activeArtifact === artifact.artifact_type ? "active" : ""}
              onClick={() => onArtifact(artifact.artifact_type)}
            >
              <FileText size={15} />
              <span>{artifactLabel(artifact)}</span>
              <small>v{artifact.version}</small>
            </button>
          ))}
          {selected && (
            <button onClick={onTrace}>
              <FlowArrow size={15} />
              <span>运行轨迹</span>
              <small>{statusLabel[detail?.latest_run?.status ?? selected.status]}</small>
            </button>
          )}
          {!selected && <p className="side-empty compact">选择一个 Bubble 后查看产物。</p>}
        </div>
      </SidebarSection>

      <SidebarSection icon={<GearSix />} title="功能">
        <div className="action-list">
          <button onClick={() => void onRerun()} disabled={!selected || busy}><ArrowClockwise /> 重新运行</button>
          <button onClick={() => void onExport()} disabled={!detail?.artifacts.length}><DownloadSimple /> 导出 Markdown</button>
          <button className="danger" onClick={() => void onDelete()} disabled={!selected}><Trash /> 删除 Bubble</button>
        </div>
      </SidebarSection>

      <div className="system-card">
        <span className={health ? "online" : "offline"} />
        <div><strong>{health ? "本地 Agent 在线" : "等待后端连接"}</strong><small>{health ? `${health.provider} / ${health.model}` : "127.0.0.1:8765"}</small></div>
      </div>
    </aside>
  );
}

function SidebarSection({ icon, title, count, children }: { icon: React.ReactNode; title: string; count?: number; children: React.ReactNode }) {
  return (
    <section className="sidebar-section">
      <div className="section-heading"><span>{icon}{title}</span>{count != null && <small>{String(count).padStart(2, "0")}</small>}</div>
      {children}
    </section>
  );
}

function CanvasHeader({ bubbles, onCreate }: { bubbles: Bubble[]; onCreate: () => void }) {
  const running = bubbles.filter((bubble) => bubble.status !== "ready").length;
  return (
    <header className="canvas-header" data-interactive>
      <div>
        <small>IDEA SPACE / {String(bubbles.length).padStart(2, "0")}</small>
        <h1>泡泡区</h1>
      </div>
      <div className="canvas-hint"><ChatCircleDots size={18} /><span>双击任意空白位置<br /><small>调出聊天栏</small></span></div>
      <div className="canvas-stats"><span><i className="working" />{running} 进行中</span><span><i className="done" />{bubbles.length - running} 已完成</span></div>
      <button className="mobile-create" onClick={onCreate} aria-label="创建 Bubble" title="创建 Bubble"><Plus /></button>
    </header>
  );
}

function BubbleNode({ bubble, selected, index, groupCount, band, canvasSize, origin, reducedMotion, onSelect }: {
  bubble: Bubble;
  selected: boolean;
  index: number;
  groupCount: number;
  band: "top" | "bottom";
  canvasSize: { width: number; height: number };
  origin?: { xRatio: number; yRatio: number };
  reducedMotion: boolean;
  onSelect: (id: string) => void;
}) {
  const size = depthMeta[bubble.depth].size;
  const target = bubblePlacement(index, groupCount, size, band, canvasSize, origin);
  const initial = origin
    ? { x: origin.xRatio * canvasSize.width - size / 2, y: origin.yRatio * canvasSize.height - size / 2, scale: 0.72, opacity: 0 }
    : { x: target.x, y: target.y, scale: 0.82, opacity: 0 };
  const running = ["draft", "running"].includes(bubble.status);
  return (
    <motion.button
      data-interactive
      className={`bubble-node ${bubble.depth} ${bubble.status} ${selected ? "selected" : ""}`}
      style={{ width: size, height: size }}
      initial={initial}
      animate={{ x: target.x, y: target.y, scale: 1, opacity: 1 }}
      exit={{ scale: 0.65, opacity: 0 }}
      transition={reducedMotion ? { duration: 0 } : { type: "spring", stiffness: 92, damping: 17, mass: 0.9 }}
      onClick={() => onSelect(bubble.id)}
      aria-label={`${bubble.name}，${depthMeta[bubble.depth].label}深度，${statusLabel[bubble.status]}`}
    >
      <span className="bubble-gloss" />
      {running && <span className="bubble-pulse" />}
      <small>{depthMeta[bubble.depth].code}</small>
      <strong>{bubble.name}</strong>
      <span className="bubble-status"><i />{statusLabel[bubble.status]}</span>
    </motion.button>
  );
}

function IdeaComposer({ point, busy, onClose, onSubmit }: {
  point: ComposerPoint;
  busy: boolean;
  onClose: () => void;
  onSubmit: (idea: string, depth: Depth, point: ComposerPoint) => Promise<void>;
}) {
  const [idea, setIdea] = useState("");
  const [depth, setDepth] = useState<Depth>("builder");
  const valid = idea.trim().length >= 10;
  const submit = () => {
    if (valid && !busy) void onSubmit(idea.trim(), depth, point);
  };
  return (
    <motion.section
      data-interactive
      className="idea-composer"
      style={{ left: point.x, top: point.y }}
      initial={{ opacity: 0, scale: 0.92, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96, y: 6 }}
      transition={{ duration: 0.2 }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="composer-title"
    >
      <header><span><Sparkle weight="fill" /> 新想法</span><button onClick={onClose} aria-label="关闭聊天栏" title="关闭"><X /></button></header>
      <label id="composer-title" htmlFor="idea-input">你想做一个什么项目？</label>
      <textarea
        id="idea-input"
        autoFocus
        value={idea}
        onChange={(event) => setIdea(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder="例如：做一个能把模糊想法拆成可执行计划的桌面 Agent…"
        rows={4}
        maxLength={5000}
      />
      <div className="composer-depths" aria-label="开发深度">
        {(Object.keys(depthMeta) as Depth[]).map((key) => {
          const Icon = key === "spark" ? Sparkle : key === "builder" ? Stack : Buildings;
          return (
            <button key={key} className={depth === key ? "active" : ""} onClick={() => setDepth(key)}>
              <Icon /> <span>{depthMeta[key].label}<small>{depthMeta[key].note}</small></span>
            </button>
          );
        })}
      </div>
      <footer><small>{idea.length}/5000 · Enter 创建，Shift + Enter 换行</small><button className="send-action" onClick={submit} disabled={!valid || busy}>{busy ? <CircleNotch className="spin" /> : <PaperPlaneTilt weight="fill" />} 创建 Bubble</button></footer>
    </motion.section>
  );
}

function ProjectDrawer({ detail, events, activeArtifact, busy, onArtifact, onConfirm, onClose }: {
  detail: BubbleDetail;
  events: RunEvent[];
  activeArtifact: string;
  busy: boolean;
  onArtifact: (type: string) => void;
  onConfirm: (answers: Record<string, string>) => Promise<void>;
  onClose: () => void;
}) {
  const run = detail.latest_run;
  const waiting = run?.status === "waiting" && run.interrupt_payload;
  const active = detail.artifacts.find((item) => item.artifact_type === activeArtifact);
  return (
    <motion.aside
      data-interactive
      className="project-drawer"
      initial={{ x: "105%" }}
      animate={{ x: 0 }}
      exit={{ x: "105%" }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      aria-label={`${detail.bubble.name} 项目详情`}
    >
      <header className="drawer-header">
        <div><span className={`status-dot ${detail.bubble.status}`} /> <small>{depthMeta[detail.bubble.depth].code} / {statusLabel[run?.status ?? detail.bubble.status]}</small><h2>{detail.bubble.name}</h2><p>{detail.bubble.raw_idea}</p></div>
        <button onClick={onClose} aria-label="关闭项目详情" title="关闭"><X /></button>
      </header>
      {detail.artifacts.length > 0 && (
        <div className="drawer-tabs">
          {detail.artifacts.map((artifact) => <button key={artifact.artifact_type} className={activeArtifact === artifact.artifact_type ? "active" : ""} onClick={() => onArtifact(artifact.artifact_type)}>{artifactLabel(artifact)}</button>)}
          <button className={!active ? "active" : ""} onClick={() => onArtifact("__trace")}>轨迹</button>
        </div>
      )}
      <div className="drawer-body">
        {waiting ? (
          <ConfirmationPanel
            key={run.id}
            questions={run.interrupt_payload!.questions}
            knownFacts={run.interrupt_payload!.known_facts}
            assumptions={run.interrupt_payload!.assumptions}
            busy={busy}
            onConfirm={onConfirm}
          />
        ) : active ? (
          <article className="markdown-document"><div className="document-meta"><span>STRUCTURED ARTIFACT</span><span>v{active.version}</span></div><ReactMarkdown>{active.markdown}</ReactMarkdown></article>
        ) : (
          <RunTrace run={run} events={events} />
        )}
      </div>
    </motion.aside>
  );
}

function ConfirmationPanel({ questions, knownFacts, assumptions, busy, onConfirm }: {
  questions: ClarifyingQuestion[];
  knownFacts: string[];
  assumptions: string[];
  busy: boolean;
  onConfirm: (answers: Record<string, string>) => Promise<void>;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => Object.fromEntries(questions.map((item) => [item.id, item.suggested_answer ?? ""])));
  const complete = questions.every((item) => answers[item.id]?.trim());
  return (
    <div className="confirmation-panel">
      <div className="confirmation-title"><Warning weight="duotone" /><span><small>HUMAN IN THE LOOP</small><h3>确认边界后继续</h3></span></div>
      <div className="scope-grid"><div><strong>已知事实</strong>{knownFacts.map((item) => <p key={item}>✓ {item}</p>)}</div><div><strong>待确认假设</strong>{assumptions.map((item) => <p key={item}>? {item}</p>)}</div></div>
      <div className="question-list">
        {questions.map((question, index) => (
          <label key={question.id}><small>Q{String(index + 1).padStart(2, "0")}</small><strong>{question.question}</strong><span>{question.why_it_matters}</span><input value={answers[question.id] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))} placeholder={question.suggested_answer ?? "输入答案"} /></label>
        ))}
      </div>
      <button className="confirm-action" disabled={!complete || busy} onClick={() => void onConfirm(answers)}>{busy ? "正在恢复工作流" : "确认并继续"}<ArrowUpRight /></button>
    </div>
  );
}

function RunTrace({ run, events }: { run?: AgentRun | null; events: RunEvent[] }) {
  const visible = events.filter((item) => ["node_started", "node_completed", "node_failed", "human_input_required"].includes(item.event_type));
  return (
    <div className="run-trace">
      <div className="trace-summary"><FlowArrow size={24} /><span><small>LANGGRAPH DURABLE RUN</small><h3>{run?.current_node ? nodeLabel[run.current_node] ?? run.current_node : "等待工作流"}</h3></span></div>
      <div className="trace-metrics"><span><small>MODEL</small>{run?.model_name ?? "未启动"}</span><span><small>EVENTS</small>{events.length}</span><span><small>THREAD</small>{run?.thread_id?.slice(0, 10) ?? "none"}</span></div>
      <div className="timeline">
        {visible.map((event) => <div key={event.id} className={event.event_type}><i /><span><strong>{nodeLabel[event.node] ?? event.node}</strong><p>{eventText(event)}</p><small>{new Date(event.created_at).toLocaleTimeString("zh-CN", { hour12: false })}{event.duration_ms != null ? ` · ${event.duration_ms}ms` : ""}</small></span></div>)}
        {!visible.length && <p className="empty-trace">工作流启动后，节点事件会出现在这里。</p>}
      </div>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="empty-state" data-interactive><span className="empty-orbit"><i /><i /><i /></span><small>YOUR IDEA SPACE IS EMPTY</small><h2>想法不用完整，<br />先让它有一个形状。</h2><p>双击泡泡区任意空白位置，输入一句想法并选择开发深度。</p><button onClick={onCreate}><Plus /> 创建第一个 Bubble</button></div>
  );
}

function LoadingState() {
  return <div className="loading-state"><CircleNotch className="spin" /><span>正在读取本地项目记忆</span></div>;
}

function ErrorToast({ message, onClose }: { message: string; onClose: () => void }) {
  return <motion.div data-interactive className="error-toast" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} role="alert"><Warning weight="fill" /><span><strong>操作未完成</strong><small>{message}</small></span><button onClick={onClose} aria-label="关闭错误提示" title="关闭"><X /></button></motion.div>;
}

function bubblePlacement(index: number, groupCount: number, size: number, band: "top" | "bottom", canvas: { width: number; height: number }, origin?: { xRatio: number; yRatio: number }) {
  const usableWidth = Math.max(260, canvas.width - 64);
  const columns = Math.max(1, Math.min(groupCount, Math.floor(usableWidth / 224)));
  const cellWidth = usableWidth / columns;
  const preferredColumn = origin ? Math.min(columns - 1, Math.floor(origin.xRatio * columns)) : index % columns;
  const usedInPreferred = Math.floor(index / columns);
  const column = groupCount <= columns ? index : (preferredColumn + index) % columns;
  const row = groupCount <= columns ? 0 : usedInPreferred;
  const x = 32 + column * cellWidth + (cellWidth - size) / 2;
  const topY = 112 + row * 220;
  const bottomY = canvas.height - size - 56 - row * 220;
  return { x: clamp(x, 24, Math.max(24, canvas.width - size - 24)), y: clamp(band === "top" ? topY : bottomY, 100, Math.max(100, canvas.height - size - 38)) };
}

function byUpdated(a: Bubble, b: Bubble) {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

function projectNameFrom(idea: string) {
  const firstLine = idea.trim().split(/[。！？!?\n]/)[0].trim();
  return firstLine.slice(0, 28) || "未命名想法";
}

function artifactLabel(artifact: Artifact) {
  const labels: Record<string, string> = { prd: "产品定义", mvp: "MVP 范围", technical_plan: "技术方案", architecture_draft: "深入设计" };
  return labels[artifact.artifact_type] ?? artifact.artifact_type;
}

function eventText(event: RunEvent) {
  if (event.event_type === "human_input_required") return "状态已持久化，等待范围确认";
  if (event.event_type === "node_failed") return String(event.payload.message ?? "节点执行失败");
  if (event.event_type === "node_started") return "节点开始执行";
  const fields = event.payload.updated_fields;
  return Array.isArray(fields) && fields.length ? `更新：${fields.join(" / ")}` : "节点执行完成";
}

function messageOf(cause: unknown) {
  return cause instanceof Error ? cause.message : "发生未知错误";
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}
