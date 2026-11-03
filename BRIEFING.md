Briefing freshness
==================
Only news scans from the last 90 minutes with at least one headline may generate a briefing. Old historical-analog files are excluded. Failed results are not cached. Successful briefing responses are cached for 60 seconds.

A visit with missing or stale news starts one background refresh per process, with a 15-minute retry cooldown. The current Render configuration uses one worker. Free hosting still sleeps; no keepalive or paid scheduler is used. Local news files may be lost on restart, so the next visit requests another scan. Feed failures display an unavailable message and retry button instead of presenting the bundled July snapshot as current. AI scoring remains subject to the existing monthly budget.

Supabase migration allow_ai_budget_and_auth_sessions was applied on 2026-11-03 to permit the spending ledger and server-side auth sessions; accounts and portfolios were unchanged.
