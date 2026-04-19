# Stasha — Upgrade Ideas

A tiered list of possible changes and improvements to turn this from a portfolio demo project into a useful personal finance tool.

---

## Cosmetic / Naming (hour or less)

1. **Rename "Client" to "Account"** — ISA, SIPP, GIA, Brokerage, etc. Makes it feel personal rather than advisor-oriented
2. **Remove "advisor" language** — update labels, seed data, and docs to feel like a personal finance tool
3. **Rename "Stasha"** — pick a name you actually want to call it
4. **Update seed data** — replace fake clients with realistic personal holdings and accounts
5. **Add favicon and branding** — polish the login page and browser tab with your own identity

---

## Small Functional Additions (a few hours each)

6. **CRUD forms in the UI** — the frontend currently has no way to create, edit, or delete accounts, holdings, assets, or transactions. Add forms/modals for all CRUD operations so users aren't dependent on the API directly
7. **Target allocation** — set a goal like 60/20/20 and show a comparison bar against actuals
7. **Currency formatting** — switch from USD to GBP throughout
8. **Holdings grouping** — show subtotals by asset type on the dashboard
9. **Dividend tracking** — record dividend payments and show yield per holding
10. **Notes on holdings** — "bought this because..." for your own reference
11. **Dark mode toggle** — add a theme switch on the frontend
12. **Search and sort on all tables** — filter by name, symbol, value, etc.

---

## Medium Features (a day or two each)

13. **Net worth tracker** — add non-investment accounts (savings, property value, debts) and show a combined picture
14. **Recurring contributions** — track monthly deposits and show contribution history over time
15. **Goal tracking** — "I want £100k in my ISA by 2030" with a progress bar and projection
16. **Watchlist** — track assets you don't own yet, with price alerts
17. **Multiple currency support** — hold USD and GBP assets, with live FX conversion
18. **Historical snapshots** — record portfolio value daily and show a line chart over time
19. **Replace yfinance** — swap to Alpha Vantage or Twelve Data for more reliable pricing
20. **Import from CSV** — upload a broker export instead of manually entering holdings
21. **Monthly summary email** — a scheduled report sent to you with key stats

---

## Bigger Builds (a week+)

22. **Budgeting layer** — track income and expenses alongside investments
23. **Tax helper** — estimate capital gains tax, track CGT allowance usage, flag ISA contribution limits
24. **Multi-user support** — proper separate accounts if you wanted a friend or partner to use it too
25. **Mobile app (PWA)** — wrap the frontend so it works from your phone home screen
26. **Celery background jobs** — auto-refresh prices on a schedule instead of on-demand
27. **PostgreSQL migration** — swap from SQLite for proper concurrency and backups
28. **Deploy to a VPS or Raspberry Pi** — always accessible with HTTPS
29. **Plaid or TrueLayer integration** — pull holdings automatically from your broker instead of manual entry
30. **AI insights** — "your portfolio is overweight in US tech" or "you haven't rebalanced in 6 months"
31. **RAG live chat assistant** — an in-app AI chatbot that has retrieval-augmented access to your portfolio data, transaction history, and account details. Ask natural language questions like "what's my best performing holding this year?", "how much have I contributed to my ISA?", or "show me all dividends from Q1". Uses an LLM (Claude API) with your portfolio data injected as context via tool use or embeddings, served through a WebSocket or SSE endpoint with a chat UI in the frontend
