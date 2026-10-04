"use client";

import { useEffect, useMemo, useState } from "react";

type Run = {
  run_id: string;
  task: string;
  workspace: string;
  status: string;
  iteration: number;
  max_iterations: number;
  tool_calls: number;
  changed_files: string[];
  verification: Record<string, unknown>;
  failures: Record<string, unknown>[];
};

type Event = { type: string; timestamp: string; data: Record<string, unknown> };

const API = process.env.NEXT_PUBLIC_FORGE_API || "http://127.0.0.1:8000";

type User = { id: number; login: string; name?: string | null; avatar_url?: string | null };
type GitHubRepo = { id: number; full_name: string; html_url: string; default_branch: string; private: boolean };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API + path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function Home() {
  const [workspace, setWorkspace] = useState("");
  const [task, setTask] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [memory, setMemory] = useState<Record<string, unknown>[]>([]);
  const [files, setFiles] = useState<string[]>([]);
  const [diff, setDiff] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [githubRepos, setGithubRepos] = useState<GitHubRepo[]>([]);
  const [githubConnected, setGithubConnected] = useState(false);

  const refresh = async () => {
    try {
      const data = await api<Run[]>("/runs");
      setRuns(data);
      if (selected) {
        const latest = data.find((r) => r.run_id === selected.run_id);
        if (latest) setSelected(latest);
      }
    } catch (e) { setError(String(e)); }
  };

  useEffect(() => {
    refresh();
    api<User>("/auth/me").then((u) => setUser(u)).catch(() => {});
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [selected?.run_id]);

  const signIn = async () => {
    const result = await api<{ url: string }>("/auth/github/login");
    window.location.href = result.url;
  };

  const connectGithub = async () => {
    const result = await api<{ url: string }>("/github/install");
    window.location.href = result.url;
  };

  const loadGithubRepos = async () => {
    try {
      const repos = await api<GitHubRepo[]>("/github/repositories");
      setGithubRepos(repos);
      setGithubConnected(true);
    } catch (e) {
      setError(String(e));
    }
  };

  const connect = async () => {
    setError("");
    try {
      const repo = await api<{ files: string[]; path: string }>("/repositories?path=" + encodeURIComponent(workspace));
      setWorkspace(repo.path);
      setFiles(repo.files);
      setMemory(await api<Record<string, unknown>[]>("/repositories/memory?path=" + encodeURIComponent(repo.path)));
    } catch (e) { setError(String(e)); }
  };

  const start = async () => {
    if (!workspace || !task.trim()) return;
    setLoading(true); setError("");
    try {
      const run = await api<{ run_id: string }>("/runs", {
        method: "POST",
        body: JSON.stringify({ workspace, task }),
      });
      const state = await api<Run>("/runs/" + run.run_id);
      setSelected(state);
      setEvents([]);
      setDiff("");
      const source = new EventSource(API + "/runs/" + run.run_id + "/stream");
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as Event;
        setEvents((prev) => [...prev, event]);
        if (event.type === "RUN_COMPLETED" || event.type === "RUN_FAILED" || event.type === "RUN_STOPPED") {
          source.close(); refresh();
        }
      };
      source.onerror = () => source.close();
      refresh();
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const selectRun = async (run: Run) => {
    setSelected(run);
    setEvents(await api<Event[]>("/runs/" + run.run_id + "/events"));
    const d = await api<{ diff: string }>("/runs/" + run.run_id + "/diff");
    setDiff(d.diff);
  };

  const stop = async () => {
    if (selected) await api("/runs/" + selected.run_id + "/stop", { method: "POST" });
  };

  const statusClass = (status: string) => status.toLowerCase();

  const currentEvents = useMemo(() => events.slice(-80), [events]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span>⚒</span><div><strong>Forge</strong><small>coding-agent runtime</small></div></div>
        <section>
          <div className="section-title">Account</div>
          {user ? (
            <>
              <div className="muted">@{user.login}</div>
              <button onClick={connectGithub}>Connect GitHub App</button>
              <button onClick={loadGithubRepos}>Load GitHub repositories</button>
            </>
          ) : (
            <button className="primary" onClick={signIn}>Sign in with GitHub</button>
          )}
        </section>
        {githubConnected && <section>
          <div className="section-title">GitHub repositories</div>
          {githubRepos.slice(0, 20).map((repo) => (
            <button className="run-row" key={repo.id} onClick={() => setWorkspace(repo.full_name)}>
              <span><strong>{repo.full_name}</strong><small>{repo.private ? "Private" : "Public"} · {repo.default_branch}</small></span>
            </button>
          ))}
        </section>}
        <section>
          <label>Repository path</label>
          <input value={workspace} onChange={(e) => setWorkspace(e.target.value)} placeholder="/path/to/repository" />
          <button onClick={connect}>Connect repository</button>
        </section>
        <section>
          <label>Task</label>
          <textarea value={task} onChange={(e) => setTask(e.target.value)} placeholder="Fix the failing tests, inspect the repository, implement the smallest coherent change, and verify it." />
          <button className="primary" onClick={start} disabled={loading || !workspace || !task.trim()}>
            {loading ? "Starting..." : "Run Forge"}
          </button>
          {selected && !["COMPLETED","FAILED","STOPPED"].includes(selected.status) && <button className="danger" onClick={stop}>Stop run</button>}
        </section>
        {error && <div className="error">{error}</div>}
        <section className="runs">
          <div className="section-title">Persistent runs</div>
          {runs.map((run) => (
            <button className={"run-row " + (selected?.run_id === run.run_id ? "active" : "")} key={run.run_id} onClick={() => selectRun(run)}>
              <span className={"dot " + statusClass(run.status)} />
              <span><strong>{run.run_id}</strong><small>{run.task.slice(0, 58)}</small></span>
            </button>
          ))}
        </section>
      </aside>

      <div className="content">
        <header>
          <div><span className="eyebrow">LOCAL-FIRST / PERSISTENT</span><h1>Agent workspace</h1></div>
          {selected && <span className={"status " + statusClass(selected.status)}>{selected.status}</span>}
        </header>

        {!selected ? (
          <div className="empty"><div className="empty-icon">⚒</div><h2>Give Forge a repository task.</h2><p>It retrieves context, uses controlled tools, edits the workspace, runs verification, and persists the full trajectory.</p></div>
        ) : (
          <>
            <div className="metrics">
              <Metric label="Iteration" value={selected.iteration + "/" + selected.max_iterations} />
              <Metric label="Tool calls" value={String(selected.tool_calls)} />
              <Metric label="Changed files" value={String(selected.changed_files?.length || 0)} />
              <Metric label="Run" value={selected.run_id} />
            </div>
            <div className="grid">
              <Panel title="Task"><p className="task">{selected.task}</p><p className="muted">{selected.workspace}</p><div className="plan"><div className="subhead">Plan</div>{(selected as Run & { plan?: string[] }).plan?.length ? (selected as Run & { plan?: string[] }).plan!.map((step, i) => <div className="plan-step" key={i}><span>{i + 1}</span>{step}</div>) : <span className="muted">Plan will appear when the agent starts planning.</span>}</div></Panel>
              <Panel title="Verification"><pre>{JSON.stringify(selected.verification || {}, null, 2)}</pre></Panel>
              <Panel title="Live trajectory" wide><div className="timeline">{currentEvents.map((e, i) => <div className="event" key={i}><span>{new Date(e.timestamp).toLocaleTimeString()}</span><strong>{e.type}</strong><code>{JSON.stringify(e.data)}</code></div>)}</div></Panel>
              <Panel title="Changed files"><ul>{(selected.changed_files || []).map((f) => <li key={f}>{f}</li>)}</ul></Panel>
              <Panel title="Repository memory"><ul>{memory.slice(0, 20).map((m, i) => <li key={i}>{String(m.content)}</li>)}</ul></Panel>
              <Panel title="Repository files"><div className="file-list">{files.slice(0, 120).map((f) => <code key={f}>{f}</code>)}</div></Panel>
              <Panel title="Git diff" wide><pre className="diff">{diff || "No diff available."}</pre></Panel>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function Panel({ title, children, wide = false }: { title: string; children: React.ReactNode; wide?: boolean }) {
  return <section className={"panel " + (wide ? "wide" : "")}><div className="panel-title">{title}</div>{children}</section>;
}
