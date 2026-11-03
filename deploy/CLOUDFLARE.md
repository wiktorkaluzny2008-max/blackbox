# Free hosting only

Current architecture: Render Free serves the Python frontend and backend;
Supabase Free stores accounts and portfolios. Cloudflare Workers Free can
optionally proxy requests to the Render URL. No Containers or paid resources
are declared in wrangler.jsonc. Do not enable paid tiers or overage billing.

Import render.yaml in Render or create a Docker web service from this repo.
Explicitly select Free, Frankfurt, main branch. APP_SECRET is a generated,
stable runtime secret; DATABASE_URL is the dedicated Blackbox Supabase session
pooler connection string. Apply supabase_schema.sql before starting the app.
Never use the unrelated YFS database. The service refuses to start without
these secrets. Configure them in Render, not in the Cloudflare Worker.

First verify the onrender.com URL. Optional Cloudflare setup: use
`npm run check` for build, `npm run deploy` for deploy, disable previews, and
set RENDER_ORIGIN to that exact https://…onrender.com origin. This value is
public; database/password secrets must stay on Render. The Worker validates
the origin and disables response caching for personalized routes.

Free services can sleep or pause. Render sleeps after 15 minutes without
traffic; Supabase may pause after 7 days of low activity. Do not bypass idle
policies with keepalive traffic. No paid background worker, cron or disk is
configured. Market news/prices refresh on demand. Container caches are ephemeral;
legacy scanner snapshots and crypto history downloads need separate review
before offering continuous background operation. 512 MB RAM may constrain ML.

Required launch verification: Docker build, startup, login, questionnaire/profile
save, portfolio reload, forced restart with persisted database state, and model
memory use. Local Docker was unavailable during preparation; live tests remain.
