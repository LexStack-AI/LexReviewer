"""Central entry point for telemetry/observability integrations (Sentry, Langfuse)."""

from observation.Langfuse.langfuse import LangfuseObservation
from observation.Sentry.sentry import SentryObservation


class ObservationProvider:
    """Best-effort initializer that wires up Sentry and Langfuse if configured."""

    def __init__(self) -> None:
        # Initialize Sentry for error tracking (optional).
        try:
            SentryObservation()
        except Exception:
            pass  # Sentry initialization is optional
        
        # Initialize Langfuse for LLM observability (optional).
        try:
            self.client = LangfuseObservation()
        except Exception:
            self.client = None  # Langfuse initialization is optional

    def get_config(self, user_id: str, document_id: str, username: str, query: str):
        """Return a Langfuse-aware graph config if Langfuse is available."""
        if self.client:
            return self.client.get_languse_config(user_id=user_id, document_id=document_id, username=username, query=query)
        return {}