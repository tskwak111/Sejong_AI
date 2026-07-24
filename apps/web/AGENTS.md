# Web app local rules

- Follow root `AGENTS.md` and contracts.
- Mobile-first: verify 390px and 430px; no horizontal overflow.
- Use semantic HTML, keyboard operation, visible focus, modal focus trap/return.
- Body contrast >= 4.5:1 and do not encode status by color only.
- Render source metadata exactly as returned by API; never invent or rewrite URLs/dates.
- Display official/event/evaluation/mock badges clearly.
- Public product pages remain `/`, `/chat`, `/admin`. The human-merged PR #8 local/private admin
  baseline may use `/admin/login`, `/admin/failures`, and `/admin/kb-candidates` only as internal
  views of the `/admin` page family; they are not public activation approval. Use tabs/cards/modals
  for other views, and require human approval before adding any further route.
- P2 UI should not be silently added.
- Keep API calls in a typed client generated/aligned from contracts.
- Add component/E2E tests for every user-visible state.
