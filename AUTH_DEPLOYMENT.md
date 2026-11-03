# Supabase Auth and Claude Haiku activation

Code supports a staged rollout. Hosting remains Cloudflare Free, Render Free, and Supabase Free. Features stay disabled until configured in Render environment settings. Never commit real keys or paste them in chat.

## Supabase Auth

Set these server-only environment variables:

- `SUPABASE_URL=https://gbhvyegvsdtomccuhupi.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY` — Blackbox project's publishable key
- `SUPABASE_SECRET_KEY` — Blackbox project's secret key (legacy service-role key also supported)
- `PUBLIC_APP_URL=https://blackbox.wiktor-kaluzny2008.workers.dev`
- `SUPABASE_AUTH_ENABLED=1` — enable only after validating keys and email delivery

Keep the existing `DATABASE_URL` and `APP_SECRET`. Configure the Supabase Auth Site URL to the PUBLIC_APP_URL. Check the email/password provider and test email confirmation delivery. Supabase's built-in email service is restricted; public signups may require a verified custom SMTP sender on a free email-service tier. Do not disable confirmation silently to work around email limits.

Existing accounts migrate on the next successful email/password login. Their legacy password is checked first; an Auth identity is created, and Supabase must verify the password before linking it. The original account ID, active portfolio ID, questionnaire, and portfolio history stay intact. Existing accounts do not all appear in Authentication > Users immediately: each appears after that owner's next password login.

Existing password hashes are PBKDF2; they cannot be copied directly into Supabase's bcrypt password field. Migration preserves the current password by submitting it to Supabase only during the authenticated login request. No plaintext password is stored. If migration fails, legacy credentials and portfolio mappings remain intact. Duplicate Auth identities are never overwritten and cannot claim an old portfolio by email alone.

New signups use Supabase's signup endpoint. With email confirmation enabled, no application session is created until confirmation and password login succeed. Pending guest portfolios remain tied to the same browser session and are adopted after login. New users should verify email, then sign in on the website.

Supabase access/refresh tokens are stored only in the private `auth_sessions` state row; the browser receives an opaque session ID in the signed HttpOnly cookie. Session tokens refresh server-side. Logout removes the stored session and revokes its provider session. The existing `blackbox_state` table must retain RLS and no grants to anon/authenticated roles; no new public grants or schemas are required.

Legacy recovery keys remain usable only before migration. After migration, Supabase is authoritative: old password hashes and recovery-key hashes are removed. Configure Supabase email recovery before public rollout; a dedicated password-reset UI is not included in this change. Google login is hidden during this rollout until Supabase Google OAuth is configured. Do not disable the Auth feature flag after real migrations as a rollback: migrated users no longer have a local password hash. Roll back to a previous version that still supports Supabase or repair configuration while preserving the mappings.

Activation acceptance checks: legacy account login retains the same portfolio; Auth Users shows its new identity; new signup/email confirmation/login works; logout and relogin retain data; another account cannot read the portfolio; disabled/deleted Auth users cannot access it.

## Claude Haiku

Owner approved a maximum of $10/month for Blackbox on 2026-11-03.

- `AI_PROVIDER=anthropic`
- `ANTHROPIC_API_KEY` — key from the owner's Anthropic API account
- `AI_MONTHLY_LIMIT_USD=10`
- `ANTHROPIC_ENABLED=1` — only after the key and provider-side spending cap are configured

Model: `claude-haiku-5-5`, using the Messages API. The prompt is limited to 24KB and output to 1000 tokens. Based on the verified November 2026 pricing ($0.10/M input and $0.50/M output for this context size), each request is conservatively reserved at $0.01 BEFORE sending. At most 1000 paid attempts per UTC calendar month are allowed, including failed attempts. Reservations persist in Postgres under `ai_budget`, serialize across workers, and stop requests when storage is unavailable. This can stop usage earlier than $10 of actual token billing. The guard covers this application only, not other applications using the same API account. Configure a separate Anthropic workspace/key with a $10 provider spending limit as an additional safeguard. Do not enable automatic credit purchases. If provider prices change, recheck the fixed reservation before enabling.

Without the API key and enable flag, no Anthropic requests are sent. Failures or exhausted budget fall back to the app's existing unavailable-AI behavior, never to another paid model. API credits are billed by Anthropic, independently of free hosting.

Tests: `python3 -m unittest discover -p 'test_*.py'`; `node test_account_ui.cjs`.
