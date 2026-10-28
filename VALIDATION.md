# Validation — v1.1 — 2026-10-28

- Python 3.12: 18 HTTP/domain tests passed with temporary SQLite databases.
- Chromium / Playwright: full storefront-to-admin-to-checkout smoke flow passed.
- Persian, English, Arabic, Spanish switching and RTL/LTR direction verified.
- Desktop 1440 px and mobile 390 px screenshots inspected; no horizontal overflow at 390 px.
- Server rejects quantities below 5, non-integers and duplicate product lines.
- Server computes prices; injected client totals and addresses are ignored.
- Samples and missing payment configuration cannot produce payable orders.
- USDT BEP-20 checkout and LTC checkout exercised through the browser with synthetic addresses; exact totals verified.
- Product editing, public wallet configuration, manual payment confirmation and order lookup exercised.
- Wallet, price, rate and product snapshots survive later catalog edits.
- Expired LTC rates, invalid wallets and unsafe status transitions rejected.
- Unauthenticated administration, cross-origin writes and missing CSRF tokens rejected.
- Backup tested with SQLite's backup API; an existing backup is not overwritten.
- JavaScript syntax checks passed. Browser flow produced no uncaught JavaScript errors and no external page requests.
- Local logos for seven services, lion mark, and generated lion hero verified. Product logo selection survives admin edits and restart; unrecognized brands and external logo URLs are rejected.
- Six clearly marked branded sample products remain unorderable until explicitly saved by the administrator. Existing catalogs are preserved on upgrade.

No real cryptocurrency transfer, Telegram message or customer delivery occurred. No public deployment was performed. The distributed archive excludes databases, admin credentials, sessions and runtime data. Chromium / Playwright are optional validation tools and are not runtime dependencies. Windows launcher is included, but native Windows execution was not available in this Linux environment.
