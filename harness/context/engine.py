from __future__ import annotations

from .repository import RepositoryScanner
from .retrieval import FileRetriever
from .models import ContextBundle

class ContextEngine:
    def __init__(self, workspace, memory_store=None, max_files: int = 10, max_file_chars: int = 6000):
        self.workspace=workspace
        self.memory=memory_store
        self.scanner=RepositoryScanner(workspace)
        self.retriever=FileRetriever(workspace,self.scanner)
        self.max_files=max_files
        self.max_file_chars=max_file_chars

    def build(self, task: str, token_budget: int = 50000) -> ContextBundle:
        memories=self.memory.search(task, limit=8) if self.memory else []
        files=self.retriever.search(task,self.max_files,self.max_file_chars)
        status=self.workspace.git("status","--short") if self.workspace.is_git_repo else ""
        diff=self.workspace.git("diff","--",".") if self.workspace.is_git_repo else ""
        bundle=ContextBundle(task,str(self.workspace.root),files,memories,status,diff)
        # Cheap, deterministic token estimate; exact usage is provider-specific.
        text=bundle.prompt()
        bundle.token_estimate=max(1,len(text)//4)
        if bundle.token_estimate > token_budget:
            # Drop lowest-ranked files until within budget.
            while len(bundle.files)>1 and bundle.token_estimate>token_budget:
                bundle.files.pop()
                bundle.token_estimate=max(1,len(bundle.prompt())//4)
        return bundle
