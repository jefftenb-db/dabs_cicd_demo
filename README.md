# dabs_cicd_demo

Demo of the [Databricks recommended CI/CD flow](https://docs.databricks.com/aws/en/dev-tools/ci-cd/#high-level-flow)
using a Declarative Automation Bundle, GitHub, GitHub Actions, and pytest.

The bundle deploys one serverless job, **Wanderbricks Daily Booking Report**, which aggregates
`samples.wanderbricks` into a `revenue_by_destination` table.

**New here? Read [docs/DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md)** for a step-by-step guide, with a
diagram, from a local code change to production.

* `src/dabs_cicd_demo/transforms.py` – pure, unit-testable transformation logic.
* `src/dabs_cicd_demo/main.py` – job entry point (reads tables, calls the transform, writes the result).
* `resources/` – job definition (Python wheel task on serverless).
* `tests/` + `fixtures/` – pytest unit tests on local Spark with small JSON fixtures.
* `.github/workflows/` – `ci.yml` (pull requests) and `cd.yml` (merge to main).

## How the high-level flow maps to this repo

| Stage | Where it happens |
|---|---|
| 1. Version control | This GitHub repo; feature branches + pull requests into `main` |
| 2. Code | Local IDE, deploy personal copy with `-t dev` |
| 3. Build | `artifacts` in `databricks.yml` builds the wheel (`uv build --wheel`) on every deploy |
| 4. Deploy | GitHub Actions → `databricks bundle deploy` (`staging` on PR, `prod` after merge + approval) |
| 5. Test | `pytest` unit tests on every PR/merge; job run in `staging` is the integration test |
| 6. Run | `databricks bundle run wanderbricks_daily_report` in CI/CD |
| 7. Monitor | Job run UI in each workspace; failure email notifications on the job |

```
feature branch ──PR──▶ CI: unit-tests ─▶ deploy-staging (dev workspace, SP, OIDC) ─▶ run job
                                                    │
                 merge to main ──▶ CD: unit-tests ─▶ [approval] ─▶ deploy-prod (prod workspace, SP, OIDC) ─▶ run job
```

## Targets

| Target | Workspace | Deployed by | Writes to |
|---|---|---|---|
| `dev` (default) | `fevm-serverless-stable-tenbosch` | You, from your laptop (`DEFAULT` profile) | `tenbosch.wanderbricks` |
| `staging` | `fevm-serverless-stable-tenbosch` | GitHub Actions as SP `dabs-cicd-demo-staging` | `tenbosch.wanderbricks_staging` |
| `prod` | `fevm-serverless-stable-tenbosch-prd` | GitHub Actions as SP `dabs-cicd-demo-prod` | `serverless_stable_tenbosch_prd_catalog.wanderbricks` |

## Authentication

GitHub Actions deploys as a service principal (never a user), using
[OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m). Each GitHub environment
(`staging`, `prod`) holds its own credentials, so a job can only reach the workspace for its environment:

* variables: `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`
* secret: `DATABRICKS_CLIENT_SECRET` (SP OAuth secret, expires 2028-10-15)

The `prod` environment also requires a reviewer's approval and only accepts deployments from `main`.

**Upgrade path: secretless OIDC.** Databricks' most secure option is
[workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github). An
account admin creates a federation policy per SP (issuer `https://token.actions.githubusercontent.com`,
audience `https://<workspace-host>/oidc/v1/token`, subject
`repo:jefftenb-db@100221386/dabs_cicd_demo@1421468708:environment:<staging|prod>`). Then, in the
workflows, set `DATABRICKS_AUTH_TYPE: github-oidc`, add `permissions: id-token: write`, and remove the
client secret.

## Runners

* `unit-tests` runs on GitHub-hosted `ubuntu-latest`.
* `deploy-staging` / `deploy-prod` run on a **self-hosted runner** (label `databricks-deploy`), because the
  FEVM workspaces only accept connections from allowlisted IPs. The runner lives in
  `~/actions-runner/dabs_cicd_demo` and needs the Databricks CLI and uv on its PATH.
  Start it before a demo with `cd ~/actions-runner/dabs_cicd_demo && ./run.sh` (Ctrl+C to stop).
* Fork PRs never reach the self-hosted runner, and workflow runs from outside contributors need approval.

## Local development

```
uv sync --dev
uv run pytest                     # requires Java 17+ locally (e.g. brew install openjdk@17)
databricks bundle deploy -t dev --profile DEFAULT
databricks bundle run wanderbricks_daily_report -t dev --profile DEFAULT
```

## Demo script

1. `git checkout -b feature/avg-booking-value`
2. In `transforms.py` add `F.avg("total_amount").alias("avg_booking_value")` to the aggregation, and
   update `test_output_columns` (and add an assertion) in `tests/test_transforms.py`.
3. `uv run pytest` locally, optionally `databricks bundle deploy -t dev` to try it in your own copy.
4. Push and open a PR → **CI** runs unit tests, then deploys and runs the job in `staging`.
   (Try pushing a broken test first to show the PR being blocked.)
5. Merge → **CD** runs unit tests, waits for approval on the `prod` environment, then deploys and runs in prod.
6. Show the job and its run history in the prod workspace (owned / run as the prod service principal).
