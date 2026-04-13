# RAG-Quest Static Web Client

Single-page vanilla-JS frontend for the v0.8 web wrapper. No build step, no
framework, no CDN — just `index.html`.

## Running

```bash
.venv/bin/python -m rag_quest serve
# → http://127.0.0.1:8000/
```

`rag_quest.web.app` mounts this directory at the root `/` via
`fastapi.staticfiles.StaticFiles`, so visiting the server's root serves
`index.html`. The mount is registered **last** so it never shadows the
API routes.

## Wire-up

| UI action                  | API call                                        |
| -------------------------- | ----------------------------------------------- |
| Page load                  | `GET /saves` → populates save picker            |
| Click **Load**             | `POST /session/load` with `{slot_id}`           |
| After load                 | `GET /session/{session_id}/state` → state panel |
| Submit turn                | `EventSource /session/{session_id}/turn/stream` |
| `event: pre_turn`          | Render world-event banner + departures          |
| `event: chunk`             | Append text to the live narrator line           |
| `event: done`              | Render module/achievement unlocks, refresh state panel |

All server-supplied text is rendered via `textContent` / `createElement`.
`innerHTML` is not used anywhere — LLM output and save-file data flow
through this page, so treating any of it as HTML would be an XSS risk.

## Event payload shapes

The web endpoints serialize pre-turn and post-turn side effects from
`rag_quest.engine.turn.PreTurnEffects` / `PostTurnEffects`:

```jsonc
// pre_turn SSE event (and POST /turn response body ["pre_turn"])
{
  "type": "pre_turn",
  "new_event": { "name": "Goblin Raid", "description": "..." } | null,
  "expired_events": ["Festival of Light", ...],
  "departed_party_members": ["Gus", ...]
}

// done SSE event (carries the same shape as POST /turn response body)
{
  "type": "done",
  "state_change": { ... StateChange asdict ... },
  "post_turn": {
    "module_transitions": [{ "id", "title", "status" }, ...],
    "achievements_unlocked": [{ "id", "name", "icon" }, ...]
  },
  "state": { ... full game_state.to_dict() ... }
}
```
