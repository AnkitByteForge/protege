"""P9's minimal P8 integration point: persisting a completed
``protege.thin_thread.ThinThreadResult`` and rehydrating it back.
"""

from .thin_thread_bridge import PersistedThinThreadRun, persist_thin_thread_result

__all__ = ["PersistedThinThreadRun", "persist_thin_thread_result"]
