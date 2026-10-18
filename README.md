# Healthcare Dashboard

A patient management dashboard for a medical practice: a patient list with search, filters,
sorting and paging; a patient chart with clinical notes and a summary; and create, edit and
delete with validation and edit-conflict detection.

React + TypeScript (Vite) · FastAPI · PostgreSQL · Docker Compose

> All patient data is synthetic. This is a demonstration project and is not HIPAA compliant.

## Run it

### Prerequisites

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with the
  Compose v2 plugin), running
- Ports 8080 and 8000 free

Node and Python are only needed to run the frontend checks and backend lint outside Docker
(see [Tests](#tests)).

### Get the code

```sh
git clone https://github.com/tpulley88/healthcare-dashboard.git
cd healthcare-dashboard
```

With the GitHub CLI: `gh repo clone tpulley88/healthcare-dashboard`. Or use **Code → Download
ZIP** on the repository page and unzip it.

### Start

```sh
cp .env.example .env          # local settings; the defaults work as they are
docker compose up --build     # first build takes a few minutes
```

Open http://localhost:8080 once the `api` container logs `Application startup complete`.
Stop with `Ctrl+C`, or `docker compose down` if started with `-d`.

To get later changes: `git pull`, then `docker compose up --build` again. New migrations run
on startup.

| What | Where |
|---|---|
| Web app | http://localhost:8080 |
| API | http://localhost:8000 (health check: `/health`) |
| API docs (OpenAPI) | http://localhost:8000/docs |

On startup the API applies migrations (Alembic), then seeds 120 synthetic patients with notes
if the database is empty. Restarts don't reseed. To start over:
`docker compose down -v && docker compose up --build`.

### Generated summaries (optional)

The patient summary works without any setup. To have a language model write the summary's
narrative, set `OPENAI_API_KEY` in `.env` (and optionally `OPENAI_MODEL`, default
`gpt-5-mini`), then run `docker compose up -d api` to apply it. See [Patient summary](#patient-summary).

### Tests

```sh
docker compose run --rm --build test                  # API: pytest against a separate database
docker compose --profile e2e run --rm --build e2e     # Browser: Playwright, with the app running
```

The browser tests need the app running (`docker compose up`). They create and delete their own
patients, and never call the language model.

Frontend unit tests, type checking, lint and formatting, from `frontend/` with Node 24:

```sh
npm ci
npm test && npm run build && npm run lint && npm run format:check
```

Backend lint: `cd backend && uv run ruff check . && uv run ruff format --check .`

## Architecture

```
browser ──▶ web (nginx :8080) ──/api──▶ api (FastAPI :8000) ──▶ db (Postgres 16)
              serves the built SPA                               not published to the host
```

The browser only talks to nginx, so the frontend and API share an origin and no CORS setup is
needed. Postgres is reachable only inside the Compose network.

**Backend** (`backend/app`)
- `routers/` hold the HTTP layer; `schemas.py` holds every validation rule (Pydantic v2);
  `models.py` is SQLAlchemy 2.0; `alembic/versions/` is the schema history.
- Routes are plain `def`, so FastAPI runs their blocking database calls in a thread pool.
- Settings come from environment variables and fail fast at startup when a required one is
  missing.

**Frontend** (`frontend/src`)
- **Server state:** TanStack Query. Caching, background refresh, retries and
  loading/error states without a global store. No client-side store is needed yet. The only
  other state is form state, kept local to the form.
- **Routing:** React Router. The list's search, filter, sort and page live in the URL, so Back,
  refresh and shared links keep the same view.
- **UI and styling:** hand-written components and one plain CSS file with design tokens. No
  component library: the app has a handful of screens, and accessible native elements (tables,
  forms, buttons) cover them without the extra dependency.
- **Tooling:** TypeScript strict, oxlint, Prettier, Vitest, Playwright.

**Routes:** `/` dashboard · `/patients` list · `/patients/new` · `/patients/:id` chart ·
`/patients/:id/edit` · anything else shows a 404 page.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{"status": "ok"}`. Liveness only; doesn't touch the database. |
| GET | `/patients` | `page`, `page_size` (≤100), `search` (any part of the name), `status`, `sort` (`name`, `age`, `last_visit_date`, `created_at`), `order` |
| GET | `/patients/{id}` | Returns an `ETag` with the record's version. |
| POST | `/patients` | 201 |
| PUT | `/patients/{id}` | Changes only the fields sent. Send `If-Match: <ETag>` to get 412 instead of overwriting someone else's edit. |
| DELETE | `/patients/{id}` | 204. Soft delete. |
| GET | `/patients/{id}/notes` | Newest first. |
| POST | `/patients/{id}/notes` | `taken_at` (with a timezone offset) and `content`. |
| DELETE | `/patients/{id}/notes/{note_id}` | 204. Soft delete, like "entered in error". |
| GET | `/patients/{id}/summary` | See below. `source=template` skips the language model. |

**Errors:** 404 for missing or deleted records (a note under the wrong patient is also 404).
422 for validation, always in FastAPI's `detail[].loc/msg` shape, including rules checked in
routes against stored data. 412 for a stale `If-Match`. Paging always ends with the patient id,
so equal sort values never repeat or skip rows between pages.

**Validation highlights:** names trimmed and required; date of birth not in the future and at
most 130 years ago; last visit not before birth; notes not before birth and not in the future
(5-minute tolerance for clock skew); US phone numbers (stored as `(617) 555-0123`), two-letter
US state codes, ZIP or ZIP+4; email syntax; allergies and conditions de-duplicated
case-insensitively. Dates are compared in the practice's timezone (`PRACTICE_TIMEZONE`), not
the server's UTC.

## Design decisions

- **Unknown vs none known.** For allergies and conditions, `null` means not recorded and `[]`
  means none known. They are never merged: "no known allergies" is a clinical statement. The
  chart's allergy banner shows the list, "No known allergies", or a warning that allergies are
  unknown.
- **Soft delete for patients and notes.** Medical records are corrected, not erased. Every read
  filters deleted rows, every route treats a deleted patient as 404, and a database trigger
  blocks hard `DELETE` on both tables.
- **Edit-conflict detection.** Each patient has a version (SQLAlchemy `version_id_col`). The
  edit form sends only changed fields with `If-Match`. On 412 it shows what the other person
  changed beside your edits and highlights overlapping fields. You can keep your changes and
  review them before saving again, or discard them; nothing is saved without a second save.
  This also covers two saves at the same instant.
- **Search without blocking.** The search box waits 300 ms after typing stops, and the
  previous page stays on screen while the next loads, so the list never blanks. The API pages
  on the server, so 100+ patients (120 are seeded) never load at once.
- **Small screens.** Below 48rem the sidebar becomes a row of links and the chart's columns
  stack. On phones the patient list keeps name, age, status, allergies and last visit (date
  of birth, conditions and phone are in the chart), and the table scrolls inside its own box.
  A browser test checks every main page at 320px for sideways scrolling.
- **No patient data in logs.** The API and nginx access logs drop query strings, so name
  searches aren't recorded. Generated-summary failures log only the error type.
- **Last visit is its own field**, not "date of the latest note": a phone note or a lab result
  isn't a visit.

## Patient summary

`GET /patients/{id}/summary` returns the name, age, blood type, status, conditions and
allergies from the database, plus a narrative built from the 10 most recent notes. It says how
many notes it covers out of the total, and their date range. The chart shows it above the full
notes.

The seeded notes are written in SOAP format (Subjective, Objective, Assessment, Plan).

- **Built-in narrative (always available):** one dated line per note, taken from the note's
  Assessment and Plan, or its opening sentence if the note isn't in SOAP format. It is a
  structured excerpt, not a synthesis, and can leave out details.
- **Generated narrative (when `OPENAI_API_KEY` is set):** a model writes one or two paragraphs
  from the note text. Only the narrative is generated; identifiers, allergies and conditions
  always come from the database, so the model can't change them. It is labeled as generated.
  - **Sent to the provider:** status, age, conditions, allergies, and the dated text of the
    recent notes. **Not sent:** name, date of birth, contact details, address, ids. Note text
    itself may still contain identifiers. Requests use `store=False`.
  - **Long notes:** each note is sent up to 4,000 characters (notes can be 10,000). The
    response's `notes_shortened` counts notes that were cut, and the chart says so, because the
    Assessment and Plan, at the end of a SOAP note, are what gets lost.
  - **Speed:** the first summary for a set of notes takes roughly 10–20 seconds. Repeats come
    from an in-memory cache keyed by the prompt, so they are instant until a note or the profile
    changes.
  - **Fallback:** no key, a provider error, or a 30-second timeout returns the built-in
    narrative with `fallback_reason` (`not_configured` or `provider_error`), and the chart says
    why. There is no retry, because the clinician is waiting.
  - **Prompt injection:** the instructions say notes are data, not instructions, and the
    model must not add diagnoses, results or recommendations that aren't in the notes. This
    reduces the risk; it doesn't remove it.

## Production considerations

What this demo would need before real patients:

- **Authentication, roles and an audit trail.** There is no login. Notes don't record who wrote
  them: with authentication, each note would get an `author_id` taken from the signed-in user
  (never from the request body), shown on the note and in the audit log, and cited by the
  summary.
- **Generated summaries with real data:** a business associate agreement and zero data
  retention with the provider, or a HIPAA-eligible hosted model; de-identification of note
  text; a log of every disclosure.
- **Summaries as stored data:** a table keyed by a fingerprint of the notes, with the model and
  prompt version, generated in the background when a note is saved, rather than a per-process
  cache. Pin the model version, add rate limits, spend caps and a circuit breaker.
- **Trust in the output:** link each statement to its source note, run automated faithfulness
  checks against an evaluation set graded by clinicians, and never let generated text enter
  the record without clinician sign-off. For long notes, send the Assessment and Plan first and
  trim the Subjective, instead of cutting from the end.
- **Structured note entry** (SOAP fields) instead of free text with headings.
- **Secrets** in a secrets manager rather than `.env`, with secret scanning in CI.

## Known limitations

- **No authentication or authorization**, and no unsaved-changes warning when leaving a form.
- **US-only formats** for phone, state and ZIP.
- **Deceased patients:** there's no date-of-death field, so age keeps counting.
- **`PUT` is a partial update** (PATCH semantics), to match the specified API. `If-Match` is an
  exact match on one ETag (no `*` or lists). `DELETE` doesn't take `If-Match`; a delete racing a
  save is still refused with 412.
- **"Unknown"** covers both "not asked" and "patient doesn't know".
- **Seed data** is illustrative: condition, allergy and status rates are plausible but not
  epidemiological.
- **The hard-delete trigger** can be bypassed by a database superuser (`TRUNCATE` or disabling
  triggers).
- **nginx error log** may include a request's query string, which can contain a name search.
- **Unknown frontend URLs** return HTTP 200 with the app's 404 page (SPA fallback); the API
  returns real 404s.
- **The summary cache** is per process: lost on restart and not shared between workers.
- **Browser tests** soft-delete the patients they create, so those rows stay in the database.

## Stretch goals

- **Advanced backend:** sorting and filtering query parameters; Alembic migrations.
- **Testing:** pytest API tests (179); Vitest unit tests for the API client, formatting, list
  URL parameters and form logic (43); Playwright end-to-end tests for the main journeys (18):
  create, chart a note, edit and delete a patient; search, filter, sort and paging, with Back
  and reload keeping the view; note validation messages and deleting a note; edit conflicts
  between two tabs; edits surviving a failed refresh; the summary; navigation, a deleted
  patient, 404 and a phone-sized screen.
- **Language-model summary** with a built-in fallback (the summary hint in Part 3).

## Project layout

```
backend/    FastAPI app, Alembic migrations, seed data, pytest suite
frontend/   React app, nginx config, Vitest and Playwright tests
docker-compose.yml   db, api, web; test and e2e profiles
.env.example         every setting, with safe local defaults
```
