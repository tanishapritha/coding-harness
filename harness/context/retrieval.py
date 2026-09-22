from __future__ import annotations

import re
from ..workspace import Workspace
from .repository import RepositoryScanner
from .models import ContextFile

STOP = {"the","and","for","with","from","this","that","fix","add","change","make","into","then","when","where","what","how","use"}

def terms(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower()) if x not in STOP}

class FileRetriever:
    def __init__(self, workspace: Workspace, scanner: RepositoryScanner):
        self.workspace=workspace
        self.scanner=scanner

    def search(self, task: str, limit: int = 10, max_chars: int = 6000) -> list[ContextFile]:
        q=terms(task)
        scored=[]
        for rel in self.scanner.files():
            name_terms=terms(rel.replace("/"," ").replace("."," "))
            score=len(q & name_terms) * 4.0
            try:
                text=self.workspace.read_file(rel)
            except Exception:
                continue
            lowered=text.lower()
            score += sum(lowered.count(t) for t in q) * 0.15
            if rel.startswith("tests/") or rel.startswith("test_"):
                if any(t in rel.lower() for t in q): score += 1.0
            if score > 0:
                scored.append((score, rel, text))
        scored.sort(key=lambda x:(-x[0],x[1]))
        if not scored:
            for rel in self.scanner.files()[:limit]:
                try: scored.append((0.1, rel, self.workspace.read_file(rel)))
                except Exception: pass
        top=scored[:limit]
        max_score=max((x[0] for x in top), default=1.0)
        result=[]
        for score,rel,text in top:
            norm=score/max_score if max_score else 0
            reason="filename/task match" if score>=1 else "repository fallback"
            result.append(ContextFile(rel,norm,reason,text[:max_chars]))
        return result
