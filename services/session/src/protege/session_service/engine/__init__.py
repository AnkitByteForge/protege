"""The P10 orchestration layer: reconstructs a live
``protege.session.orchestrator.SessionOrchestrator`` per request from P9-
persisted state, drives it exactly as ``protege.thin_thread.engine`` drives
one in-process, and persists the result back through the P9 repositories.

Nothing here duplicates the FSM transition table (``packages/session-fsm``
remains the sole transition authority) or reimplements P2 learning-engine
math -- this package only sequences existing calls and moves their results
across the HTTP request boundary a single in-process run does not have to
cross. See ``runtime.py``'s module docstring for the full design.
"""
