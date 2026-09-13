# evals — evaluation harness

The evaluation harness lands in P24: golden sets (120 diagnosis, 200 Sprout
fidelity), 500 simulated learners with known ground-truth misconceptions, and
CI gates (F1 ≥ 0.75, fidelity ≥ 0.90, answer-leak = 0.000 — see v1.0 §26 and
docs/DECISIONS.md D3). `make eval` exists now and is an intentional no-op until
then.

Intentionally empty at P0.
