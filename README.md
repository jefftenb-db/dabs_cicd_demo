# dabs_cicd_demo

Demo of the [Databricks recommended CI/CD flow](https://docs.databricks.com/aws/en/dev-tools/ci-cd/#high-level-flow)
using a Declarative Automation Bundle, GitHub, GitHub Actions, and pytest.

The bundle deploys one serverless job, **Wanderbricks Daily Booking Report**, which aggregates
`samples.wanderbricks` into a `revenue_by_destination` table.

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

## Authentication (no stored secrets)

GitHub Actions authenticates with [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github):
each service principal has a federation policy that trusts GitHub's OIDC tokens for this repo **and** a
specific GitHub environment (`staging` or `prod`). The workflows only need the non-secret environment
variables `DATABRICKS_HOST` and `DATABRICKS_CLIENT_ID` (set on the GitHub environments) plus
`DATABRICKS_AUTH_TYPE=github-oidc` and `permissions: id-token: write`.

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
