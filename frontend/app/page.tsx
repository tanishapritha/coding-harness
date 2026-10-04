"use client";

import { useEffect, useMemo, useState } from "react";

type Run = {
  run_id: string; task: string; workspace: string; status: string; iteration: number;
  max_iterations: number; tool_calls: number; changed_files: string[];
  verification: Record<string, unknown>; failures: Record<string, unknown>[]; plan?: string[];
};
type Event = { type: string; timestamp: string; data: Record<string, unknown> };
type User = { id: number; login: string; name?: string | null; avatar_url?: string | null };
type GitHubRepo = { id: number; full_name: string; html_url: string; default_branch: string; private: boolean };

const API = process.env.NEXT_PUBLIC_FORGE_API || "http://127.0.0.1:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API + path, {
    ...init, credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const terminalEvent = (type: string) => /COMMAND|TEST|EXEC|TOOL/.test(type);

export default function Home() {
  const [workspace, setWorkspace] = useState("");
  const [task, setTask] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [files, setFiles] = useState<string[]>([]);
  const [diff, setDiff] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [connected, setConnected] = useState(false);
  const [workspaceId, setWorkspaceId] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [prUrl, setPrUrl] = useState("");
  const [error, setError] = useState("");
  const [repoPicker, setRepoPicker] = useState(false);

  const refresh = async () => {
    try {
      const data = await api<Run[]>("/runs");
      setRuns(data);
      if (selected) {
        const latest = data.find(r => r.run_id === selected.run_id);
        if (latest) setSelected(latest);
      }
    } catch (e) { setError(String(e)); }
  };

  useEffect(() => {
    refresh();
    api<User>("/auth/me").then(setUser).catch(() => {});
    const timer = setInterval(refresh, 2500);
    return () => clearInterval(timer);
  }, [selected?.run_id]);

  const signIn = async () => { const r = await api<{url:string}>("/auth/github/login"); window.location.href = r.url; };
  const connectGithub = async () => { const r = await api<{url:string}>("/github/install"); window.location.href = r.url; };

  const loadRepos = async () => {
    try { setRepos(await api<GitHubRepo[]>("/github/repositories")); setConnected(true); setRepoPicker(true); }
    catch (e) { setError(String(e)); }
  };

  const chooseRepo = async (repo: GitHubRepo) => {
    try {
      setError("");
      const w = await api<{workspace_id:string}>("/cloud/workspaces", {
        method:"POST", body:JSON.stringify({repo_full_name:repo.full_name,base_branch:repo.default_branch})
      });
      setWorkspaceId(w.workspace_id);
      setWorkspace(repo.full_name);
      setRepoPicker(false);
      setFiles([]);
      setTask("");
    } catch (e) { setError(String(e)); }
  };

  const start = async () => {
    if (!workspaceId || !task.trim()) return;
    setError(""); setPrUrl("");
    try {
      const r = await api<{run_id:string}>("/cloud/runs", {
        method:"POST", body:JSON.stringify({workspace_id:workspaceId,task})
      });
      const state = await api<Run>("/runs/" + r.run_id);
      setSelected(state); setEvents([]); setDiff("");
      const source = new EventSource(API + "/runs/" + r.run_id + "/stream");
      source.onmessage = m => {
        const e = JSON.parse(m.data) as Event;
        setEvents(prev => [...prev,e]);
        if (/RUN_COMPLETED|RUN_FAILED|RUN_STOPPED/.test(e.type)) { source.close(); refresh(); }
      };
      source.onerror = () => source.close();
      refresh();
    } catch (e) { setError(String(e)); }
  };

  const selectRun = async (run: Run) => {
    setSelected(run);
    try {
      setEvents(await api<Event[]>("/runs/" + run.run_id + "/events"));
      setDiff((await api<{diff:string}>("/runs/" + run.run_id + "/diff")).diff);
    } catch (e) { setError(String(e)); }
  };

  const stop = async () => { if (selected) await api("/runs/" + selected.run_id + "/stop",{method:"POST"}); };
  const publish = async () => {
    if (!selected || !workspaceId) return;
    setPublishing(true); setError("");
    try {
      const r = await api<{pr_url:string}>("/cloud/publish", {
        method:"POST", body:JSON.stringify({workspace_id:workspaceId,title:selected.task.slice(0,80),body:"Created by Forge."})
      });
      setPrUrl(r.pr_url);
    } catch (e) { setError(String(e)); } finally { setPublishing(false); }
  };

  const latestEvents = useMemo(() => events.slice(-40), [events]);
  const active = selected && !["COMPLETED","FAILED","STOPPED"].includes(selected.status);
  const passed = selected?.status === "COMPLETED";

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">F</span><strong>Forge</strong><span className="brand-badge">BETA</span></div>
        <div className="top-center">
          {workspace ? <><span className="repo-dot" /> <strong>{workspace}</strong><span className="branch">forge/{workspaceId || "workspace"}</span></> : <span className="muted">No workspace selected</span>}
        </div>
        <div className="top-actions">
          <span className="secure"><i /> sandboxed</span>
          {user ? <button className="avatar" title={user.login}>{user.login.slice(0,1).toUpperCase()}</button> : <button className="ghost" onClick={signIn}>Sign in with GitHub</button>}
        </div>
      </header>

      <div className="layout">
        <aside className="left">
          <div className="sidebar-head"><span>Workspace</span><button className="icon-btn" onClick={loadRepos}>+</button></div>
          <button className="repo-select" onClick={loadRepos}>
            <span className="repo-icon">⌘</span>
            <span><strong>{workspace || "Select repository"}</strong><small>{workspace ? "GitHub workspace" : "Connect a repository to begin"}</small></span>
            <span>⌄</span>
          </button>

          {repoPicker && <div className="repo-menu">
            <div className="menu-title">Your repositories</div>
            {repos.slice(0,12).map(repo => <button className="repo-item" key={repo.id} onClick={() => chooseRepo(repo)}>
              <span className="repo-icon small">⌘</span><span><strong>{repo.full_name}</strong><small>{repo.private ? "Private" : "Public"} · {repo.default_branch}</small></span>
            </button>)}
            {!repos.length && <div className="muted pad">Connect the Forge GitHub App first.</div>}
          </div>}

          {workspace && <div className="tree">
            <div className="tree-title">Files <span>{files.length}</span></div>
            {files.slice(0,70).map(f => <div className="tree-file" key={f}><span>{f.includes("/") ? "◇" : "□"}</span>{f}</div>)}
          </div>}

          <div className="sidebar-bottom">
            <div className="tree-title">Recent runs</div>
            {runs.slice(0,8).map(run => <button className={"history " + (selected?.run_id===run.run_id ? "selected":"")} key={run.run_id} onClick={() => selectRun(run)}>
              <span className={"run-status " + run.status.toLowerCase()} /><span><strong>{run.task.slice(0,31)}</strong><small>{run.run_id} · {run.status.toLowerCase()}</small></span>
            </button>)}
          </div>
        </aside>

        <section className="main">
          {!selected ? (
            <div className="hero">
              <div className="hero-mark">F</div>
              <div className="kicker">AI SOFTWARE ENGINEERING</div>
              <h1>Ship code with an agent<br/><em>you can trust.</em></h1>
              <p>Forge gives coding agents a real workspace, controlled tools, verification, persistent runs, and a clean path from task to pull request.</p>
              <div className="start-card">
                <div className="start-row"><span className="spark">✦</span><textarea value={task} onChange={e=>setTask(e.target.value)} placeholder="What should Forge build, fix, or investigate?" /></div>
                <div className="start-footer"><span>{workspace ? <><b>{workspace}</b> · isolated workspace</> : "Select a repository to start"}</span><button className="run-btn" onClick={start} disabled={!workspaceId || !task.trim()}>Run agent <span>⌘↵</span></button></div>
              </div>
              <div className="capabilities"><span>Context-aware</span><span>Sandboxed execution</span><span>Tests & verification</span><span>GitHub PRs</span></div>
            </div>
          ) : (
            <>
              <div className="run-header">
                <div><div className="kicker">AGENT RUN · {selected.run_id}</div><h1>{selected.task}</h1><div className="run-meta"><span className={"live-dot "+(active?"pulse":"")} /> {active ? selected.status.toLowerCase() : selected.status.toLowerCase()} · {selected.iteration}/{selected.max_iterations} iterations · {selected.tool_calls} tool calls</div></div>
                {active ? <button className="stop-btn" onClick={stop}>Stop run</button> : passed ? <button className="publish-btn" onClick={publish} disabled={publishing}>{publishing ? "Opening PR…" : "Commit & open PR ↗"}</button> : null}
              </div>

              <div className="run-grid">
                <div className="work-card activity-card">
                  <div className="card-head"><span>Agent activity</span><span className="live-label">{active ? "LIVE" : "COMPLETE"}</span></div>
                  <div className="activity">
                    {latestEvents.length ? latestEvents.map((e,i) => <div className="activity-row" key={i}><span className="activity-time">{new Date(e.timestamp).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</span><span className="activity-icon">{terminalEvent(e.type) ? "›" : "✓"}</span><span className="activity-name">{e.type.replaceAll("_"," ").toLowerCase()}</span><code>{JSON.stringify(e.data).slice(0,180)}</code></div>) : <div className="empty-inline">Waiting for agent events…</div>}
                  </div>
                </div>

                <div className="work-card">
                  <div className="card-head"><span>Plan</span><span>{selected.plan?.length || 0} steps</span></div>
                  <div className="plan-list">{selected.plan?.length ? selected.plan.map((s,i)=><div className="plan-item" key={i}><span>{i+1}</span>{s}</div>) : <div className="empty-inline">Planning in progress…</div>}</div>
                </div>

                <div className="work-card">
                  <div className="card-head"><span>Verification</span><span className={passed?"good":""}>{passed ? "PASSED" : selected.status === "FAILED" ? "FAILED" : "PENDING"}</span></div>
                  <pre className="verify">{JSON.stringify(selected.verification || {},null,2)}</pre>
                </div>

                <div className="work-card">
                  <div className="card-head"><span>Changed files</span><span>{selected.changed_files?.length || 0}</span></div>
                  <div className="changed">{(selected.changed_files||[]).map(f=><div key={f}><span>◇</span>{f}</div>)}{!selected.changed_files?.length&&<div className="empty-inline">No changes yet.</div>}</div>
                </div>

                <div className="work-card diff-card">
                  <div className="card-head"><span>Git diff</span><span>{diff ? "Working tree" : "No changes"}</span></div>
                  <pre className="diff">{diff || "Diff will appear as Forge edits the workspace."}</pre>
                </div>
              </div>

              {prUrl && <div className="pr-banner"><span>✓</span><div><strong>Pull request created</strong><small>Your changes are ready for review.</small></div><a href={prUrl} target="_blank" rel="noreferrer">Open on GitHub ↗</a></div>}

              <div className="composer run-composer">
                <span className="spark">✦</span><input value={task} onChange={e=>setTask(e.target.value)} placeholder="Ask Forge to continue, fix a test, or make another change…" /><button onClick={start} disabled={!workspaceId || !task.trim() || !!active}>↗</button>
              </div>
            </>
          )}
          {error && <div className="toast error-toast">{error}</div>}
        </section>
      </div>
    </main>
  );
}
