# infra — deployment infrastructure

Terraform for AWS deployment arrives in P27+ (roadmap). Nothing deployable
lives here yet; the hackathon deployment is one container plus managed Postgres
(RDS `db.t4g.micro` + pgvector) and object storage behind a `StorageAdapter`
(addendum §8).

**Manual Day-0 actions that are not code** (roadmap P0 / addendum §2.3):

- Create the NVIDIA account; request the credit increase immediately; verify
  actual metering and rate limits at `build.nvidia.com/settings` — do not trust
  blog figures.
- Register a second free overflow provider so a depleted quota cannot stop the
  build (addendum §2.4).
- Link the repo to a Vercel project so PRs produce preview deployments.
- ghcr.io package namespace: created by the first image push (P27).
- GitHub OIDC role for AWS: stubbed with Terraform (P27+).
