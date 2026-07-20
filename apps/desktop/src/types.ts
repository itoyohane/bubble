export type Depth = "spark" | "builder" | "architect";
export type BubbleStatus = "draft" | "running" | "waiting" | "ready" | "failed" | "cancelled";
export type RunStatus = "queued" | "running" | "waiting" | "completed" | "failed" | "cancelled";

export interface Bubble {
  id: string;
  name: string;
  raw_idea: string;
  depth: Depth;
  status: BubbleStatus;
  created_at: string;
  updated_at: string;
}

export interface ClarifyingQuestion {
  id: string;
  question: string;
  why_it_matters: string;
  suggested_answer?: string | null;
}

export interface InterruptPayload {
  type: string;
  questions: ClarifyingQuestion[];
  known_facts: string[];
  assumptions: string[];
}

export interface AgentRun {
  id: string;
  bubble_id: string;
  thread_id: string;
  status: RunStatus;
  current_node?: string | null;
  provider: string;
  model_name: string;
  prompt_version: string;
  error?: string | null;
  interrupt_payload?: InterruptPayload | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}

export interface RunEvent {
  id: number;
  run_id: string;
  node: string;
  event_type: string;
  payload: Record<string, unknown>;
  duration_ms?: number | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  bubble_id: string;
  artifact_type: string;
  schema_data: Record<string, unknown>;
  markdown: string;
  version: number;
  created_at: string;
}

export interface BubbleDetail {
  bubble: Bubble;
  artifacts: Artifact[];
  latest_run?: AgentRun | null;
}

export interface Health {
  status: string;
  version: string;
  provider: string;
  model: string;
}
