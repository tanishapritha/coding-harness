from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class SQLiteMemory:
    def __init__(self, db_path: str | Path, repository_id: str):
        self.db_path=Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.repository_id=repository_id
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        with self._connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, content TEXT NOT NULL,
                source_run TEXT, confidence REAL NOT NULL DEFAULT 0.7,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(repository_id, content)
            )""")

    def remember(self, content: str, source_run: str | None = None, confidence: float = 0.7):
        content=content.strip()
        if not content: return None
        now=datetime.now(timezone.utc).isoformat()
        mid=hashlib.sha256(f"{self.repository_id}:{content}".encode()).hexdigest()[:16]
        with self._connect() as c:
            c.execute("""INSERT INTO memories(id,repository_id,content,source_run,confidence,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(repository_id,content) DO UPDATE SET
                       confidence=max(confidence,excluded.confidence), source_run=excluded.source_run, updated_at=excluded.updated_at""",
                      (mid,self.repository_id,content,source_run,confidence,now,now))
        return mid

    def search(self, query: str, limit: int = 8) -> list[dict]:
        words=[w.lower() for w in query.split() if len(w)>2]
        with self._connect() as c:
            rows=c.execute("SELECT id,content,source_run,confidence,updated_at FROM memories WHERE repository_id=? ORDER BY confidence DESC, updated_at DESC",(self.repository_id,)).fetchall()
        if not words: selected=rows[:limit]
        else:
            scored=[]
            for row in rows:
                score=sum(w in row[1].lower() for w in words)
                if score: scored.append((score,row))
            scored.sort(key=lambda x:(-x[0],-x[1][3]))
            selected=[r for _,r in scored[:limit]]
        return [{"id":r[0],"content":r[1],"source_run":r[2],"confidence":r[3],"updated_at":r[4]} for r in selected]

    def all(self):
        with self._connect() as c:
            rows=c.execute("SELECT id,content,source_run,confidence,updated_at FROM memories WHERE repository_id=? ORDER BY updated_at DESC",(self.repository_id,)).fetchall()
        return [{"id":r[0],"content":r[1],"source_run":r[2],"confidence":r[3],"updated_at":r[4]} for r in rows]
