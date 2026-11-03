# Cloudflare deployment

The Worker routes all requests to a single named Python Container, keeping the
frontend and API on one origin. This requires Workers Paid plus container usage.

In Workers Builds, select this repository and main branch. Use `npm run check`
as the build command and `npm run deploy` as deploy command. Disable preview
builds until a separate preview database is configured. Dependencies are pinned.

Configure APP_SECRET (stable random signing secret) and DATABASE_URL (dedicated
Blackbox Supabase Postgres connection) as Worker runtime secrets. Apply
supabase_schema.sql to that project first. Do not put secrets into source or
ordinary build variables. Optional AI/market provider secrets are forwarded by
the Worker. Without the two required secrets the Worker responds 503 and does
not start the app. Never use the unrelated YFS database for this project.

The database stores accounts and portfolios. Container disk is ephemeral:
news/analogue caches are rebuilt and historical scanner outputs are not durable.
This initial package does not configure continuous scanning or scheduled model
refresh. The on-demand market evidence screen fetches fresh public news/prices.
The legacy crypto model can require substantial data downloads on cold start.

Before launch: build the image; test startup, registration/login, save/reload,
and forced container restart against a test database. Docker was not available
on the preparation machine, so the image build and live persistence checks are
still required. Existing model limitations are documented in MODEL_AUDIT.md.
