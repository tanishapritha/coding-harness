from __future__ import annotations

import os
from contextlib import contextmanager

class TraceRecorder:
    def __init__(self, run_id: str):
        self.run_id=run_id
        self.enabled=bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
        self._langfuse=None
        self._trace=None
        if self.enabled:
            try:
                from langfuse import get_client
                self._langfuse=get_client()
            except Exception:
                self.enabled=False

    @contextmanager
    def span(self, name: str, metadata: dict | None=None):
        if not self.enabled:
            yield None
            return
        try:
            with self._langfuse.start_as_current_observation(as_type="span", name=name, metadata=metadata or {}) as span:
                yield span
        except Exception:
            yield None

    def generation(self, name: str, model: str, input_data, output_data=None, metadata=None):
        if not self.enabled: return
        try:
            with self._langfuse.start_as_current_observation(as_type="generation", name=name, model=model, input=input_data, metadata=metadata or {}) as gen:
                if output_data is not None: gen.update(output=output_data)
        except Exception:
            pass

    def flush(self):
        if self.enabled and self._langfuse:
            try: self._langfuse.flush()
            except Exception: pass
