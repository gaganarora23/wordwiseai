# WordWise — V0 Product and Course Delivery Specification

**Document status:** V0 implementation baseline\
**Specification version:** 0.4\
**API contract version:** 0.4.0\
**Last updated:** November 14, 2026

## 1. Purpose and product vision

WordWise is a child-friendly vocabulary-learning web application for
students from Kindergarten through Grade 12. It helps a child learn a
small daily set of vocabulary words, practice their meanings, receive
immediate feedback, and gradually build mastery through repeated
practice.

The V0 product scope is a simple, dependable learning experience—not a
feature-heavy platform. V0 describes the product feature baseline; the
course project delivery also includes engineering-quality work such as
tests, deployment, CI/CD, observability, alerting, and an incident
responder-agent workflow. Those delivery requirements do not expand the
child-facing product feature scope. The app should be easy for a parent to set up,
easy for a child to use independently, and careful about the amount of
personal information it collects.

## 2. V0 goals

-   Support multiple child profiles on one browser/device.
-   Let a parent select each child's grade and daily word goal.
-   Present curated, age-appropriate vocabulary in a simple
    one-word-at-a-time learning flow.
-   Assess understanding with a consistent multiple-choice quiz.
-   Track learning, mastery, and words needing review separately.
-   Give parents a lightweight progress dashboard for each selected child,
    including learning activity, vocabulary progress, quiz performance,
    words needing review, and recent session history.
-   Keep the experience account-free: no registration, login, or
    account-management workflows.
-   Persist profiles and learning progress in PostgreSQL through a
    Python FastAPI backend.
-   Provide a stable OpenAPI contract for the Lovable-generated
    frontend; initial frontend calls may use conforming mock responses.
-   Run the complete local stack with one Docker Compose command.

## 3. Explicit V0 non-goals

The following are not part of the initial V0 release unless deliberately
added through a later specification change:

-   User registration, login, authentication, and account-management
    workflows.
-   Household ownership, multi-tenant authorization, and production
    identity management.
-   Subscription or payment functionality.
-   AI-generated vocabulary or questions at runtime.
-   Full Progressive Web App (PWA) installation and service-worker-based
    offline support.
-   Audio pronunciation.
-   Advanced spaced-repetition scheduling.
-   Multiple quiz question formats.
-   Teacher/classroom administration, class cohorts, or school
    integrations.
-   Advanced parent analytics, predictive insights, AI-generated
    recommendations, cross-child comparisons, and downloadable reports.

**Offline clarification:** PostgreSQL is server-side relational storage;
it does not, by itself, make the website available offline. Full offline
behavior is deferred with PWA/service-worker support. Do not promise
offline access in V0.

## 4. Target users and profiles

### 4.1 Users

-   **Parent:** creates, edits, and deletes child profiles and sets each
    child's grade and daily goal.
-   **Child/student:** selects their profile, learns words, completes
    quizzes, and reviews words.

### 4.2 Profile model

The application supports multiple child profiles in one shared demo instance.
The profile picker lists every profile in that instance; there is no concept
of a private household or owner.

Each profile contains: - Nickname (not full legal name; 1–20 characters). - Grade
(Kindergarten through Grade 12). - Daily goal (5 or 10 words). -
Persisted learning history and word mastery state.

Avoid collecting unnecessary personal information about children. V0
does not require an email address, phone number, date of birth, or full
name.

### 4.3 Profile management

-   A parent can create and edit profiles.
-   A parent can change a child's grade and daily goal.
-   A parent can delete a profile.
-   Profile deletion must be deliberate and resistant to accidental
    taps:
    1.  The parent initiates deletion.
    2.  The parent must type exactly `DELETE` in uppercase; lowercase or
        additional characters do not qualify.
    3.  The parent must complete a separate final confirmation.
-   Successful deletion permanently removes the profile and all associated
    learning history. There is no undo or recovery. This UI safeguard is
    not authentication or proof of parental identity.

## 5. Platform and architecture

### 5.1 V0 architecture

-   **Frontend:** Responsive website generated with Lovable. The
    frontend may use mock API calls initially.
-   **Backend:** Python FastAPI exposing versioned REST endpoints.
-   **Database:** PostgreSQL.
-   **Runtime:** Docker Compose starts the frontend, backend, and
    database.
-   **API contract:** OpenAPI 3.1 is the source of truth for
    frontend/backend integration. Mock calls must conform to the same
    request and response schemas as the real API.
-   **Vocabulary:** Curated JSON files ingested into PostgreSQL with
    repeatable Python scripts.
-   **No runtime AI dependency:** Vocabulary, definitions, examples,
    syllables, and quiz options are curated before release.

No account management is an intentional V0 constraint. There is no
registration, login, authentication, household account, or user identity
management. This is a prototype/demo architecture, not a secure
multi-user production service. Do not expose it publicly with sensitive
data or imply profile records are private from other users of the same
deployed instance.

### 5.2 Suggested application modules

-   **Profile Manager:** create, edit, select, and delete child
    profiles.
-   **Content Loader:** loads the vocabulary content for the selected
    grade.
-   **Learning Flow:** presents words and learning information.
-   **Quiz Engine:** presents questions, records answers, hints, and
    feedback.
-   **Mastery and Review Engine:** updates mastery streaks and
    identifies words needing review.
-   **API Client:** calls FastAPI endpoints defined by the OpenAPI
    contract; mock mode returns the same response shapes.
-   **Persistence Layer:** backend repositories store profiles,
    sessions, answers, results, and mastery state in PostgreSQL.

### 5.3 Suggested database entities

The implementation may use equivalent schema names, but PostgreSQL must
persist the following concepts:

-   `children`: profile ID, nickname, grade, daily goal, creation/update
    timestamps.
-   `sessions`: session ID, child profile ID, mode (`daily` or
    `review`), phase (`learning` or `quiz`), status (`in_progress`,
    `completed`, or `abandoned`), fixed word order, current position,
    timestamps, and completion/abandonment state.
-   `session_words`: session ID, word ID, and display order; enforce
    `UNIQUE(session_id, word_id)` so a word occurs at most once per
    session.
-   `answers`: session ID, word ID, selected option, correctness,
    whether a hint was used, and answer timestamp; enforce one answer
    per word per session.
-   `quizResults`: session ID, score, correct/incorrect counts, and
    review-word IDs.
-   `wordMastery`: child profile ID, word ID, status,
    consecutive-correct count, last-practiced timestamp, and review
    flag.

Use stable UUIDs (or equivalent stable identifiers) for profiles, words,
questions, and sessions. Do not rely on display text as an identifier. A
profile is an application data record only; it is not an authenticated
identity or account.

### 5.5 Repository organization and source control

The course project must be submitted through **one GitHub repository link**
that contains both the frontend and backend services. WordWise will therefore
use a **monorepo**: the frontend and backend remain separate applications
and independently buildable/deployable services, but their source code,
API contract, database assets, tests, documentation, and delivery workflows
are maintained in one repository. A single repository does not mean a single
runtime service or container.

Recommended repository layout:

```text
wordwise/
├── frontend/                  # Lovable-generated UI application
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── backend/                   # Python FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── scripts/                # Vocabulary ingestion and utilities
│   ├── data/                   # Grade-specific curated JSON files
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── database/                   # SQL, migrations, and database setup assets
├── tests/                      # Cross-service/integration tests, if needed
├── docs/                       # Architecture, workflow, and deployment docs
├── .github/
│   └── workflows/              # CI/CD workflows
├── openapi.yaml                # Authoritative API contract
├── docker-compose.yml          # Local full-stack orchestration
├── AGENTS.md                   # Agent/team instructions and project context
├── SPECIFICATION.md            # Product and implementation specification
└── README.md                   # Setup, run, test, and project overview
```

Repository conventions:

- Keep the Lovable-generated frontend under `frontend/` and the FastAPI
  service under `backend/`. Lovable may be used as the UI development
  environment; the resulting frontend source must be synchronized into the
  `frontend/` directory of this repository.
- Keep `openapi.yaml` at the repository root as the authoritative contract
  shared by frontend mocks and the FastAPI implementation. Avoid maintaining
  independent, conflicting copies of the API definition.
- Keep vocabulary source JSON and ingestion scripts with the backend, since
  they are backend-owned content and data-loading concerns.
- Use `docker-compose.yml` at the root to orchestrate the frontend, backend,
  and PostgreSQL services for local development. Each application may have
  its own Dockerfile and deployment lifecycle.
- Keep service-specific tests close to their service; use the root `tests/`
  directory for cross-service integration tests where appropriate.
- Keep CI/CD workflows, agent instructions, architecture documentation,
  and the README in the same repository so the submitted link provides a
  complete view of the project.
- The README must document prerequisites, environment configuration, how
  to start the complete stack, how to run tests, and the deployed application
  and API locations when available.

The exact folder names may evolve during implementation, but the single-repo
requirement and clear separation of frontend, backend, and shared project
assets are the baseline. This repository organization does not change the
V0 product features or the OpenAPI contract.

### 5.4 Persistence and failure handling

-   Save progress to PostgreSQL through the backend as the child works.
-   Preserve enough session state to restore an in-progress session
    after a browser refresh, including the selected question order and
    answers already submitted.
-   Do not reshuffle or silently replace a question when restoring an
    interrupted session.
-   If an API or database save fails, show a clear error and do not
    claim the progress was saved.
-   The V0 deployment has no authentication or authorization boundary.
    Anyone who can reach the application/API may be able to view or
    modify profile and learning data. Treat this as demo data only.
-   Docker Compose must configure a persistent PostgreSQL volume so data
    survives container restarts.

## 6. Vocabulary content

### 6.1 Grade coverage and quantity

-   Support Kindergarten through Grade 12.
-   V0 content target: 50 curated words per grade, approximately 650
    words total.
-   Content must be age-appropriate and suitable for the intended grade.

### 6.2 Word content fields

Each vocabulary entry should include, at minimum:

-   Stable word ID.
-   Word.
-   Grade association.
-   Student-friendly definition.
-   Example sentence.
-   Syllable breakdown as text (for example, `ba · na · na`).
-   Content version or equivalent version metadata.

Quiz content associated with each word must include: - One correct
meaning. - Four prewritten answer options in total. - Exactly one
correct option. - A short explanation suitable for immediate feedback.

Content is curated and reviewed before release. V0 does not generate
words, definitions, examples, or answer options dynamically with an AI
service.

### 6.3 Content delivery

-   The frontend requests vocabulary for the selected child's grade from
    the backend rather than loading all grades at once.
-   The backend reads vocabulary records from PostgreSQL.
-   If the selected grade changes, the frontend requests that grade's
    content from the API.
-   If the app cannot load required content, explain the problem and
    provide a retry path rather than presenting an incomplete session.

### 6.4 Vocabulary ingestion

-   The release content target is 50 curated vocabulary words for each grade
    from Kindergarten through Grade 12 (650 records total). A reduced test
    fixture may be used during development, but it must not be treated as
    release-ready content.
-   Store source content as one JSON file per grade under a backend data
    directory.
-   Provide a Python ingestion command/script that validates the files
    and inserts or updates vocabulary records in PostgreSQL.
-   The script must be idempotent: rerunning it must not create
    duplicate words.
-   Validate required fields, grade association, stable word IDs,
    syllable data, and exactly four quiz options with exactly one
    correct answer.
-   Report per-grade counts and validation failures. The expected
    successful total is 650 words.

## 7. Learning experience

### 7.1 Daily goal

-   The parent sets a daily goal of either 5 or 10 words for each child.
-   A learning session presents the selected number of words for that
    session, subject to available content and review selection.

### 7.2 Word presentation

-   Show one vocabulary word per screen/card.
-   Present the word, student-friendly definition, and example sentence.
-   Show the curated syllable breakdown as text.
-   Show a visual progress bar and a numeric position/count, such as "3
    of 10".
-   Keep the interaction clear and child-friendly.

### 7.3 Word selection

Daily word selection is deterministic in V0 so mock and backend behavior
match. For a daily session, the server selects the requested number of
unique words using this priority order:

1. Words currently flagged `NEEDS_REVIEW`.
2. Words in `LEARNING` state that are not already selected.
3. Words in `NEW` state that are not already selected.
4. Words in `MASTERED` state that are not already selected.

Within each priority group, select least-recently-practiced first; words
never practiced come before previously practiced words. Break remaining
ties by stable word ID ascending. This is a simple deterministic rule,
not an advanced spaced-repetition algorithm. A word can occur only once
in a session, even if it qualifies for multiple groups.
-   Targeted review sessions accept an explicit list of 1 to 10 unique
    word IDs from that child's review pool. Review sessions may contain
    fewer than five words.
-   A daily session must contain exactly 5 or exactly 10 unique words,
    matching the requested goal. Never repeat a word or silently return a
    shorter daily session.
-   If fewer than the requested number of eligible words exist for that
    grade, reject session creation with HTTP 409 `INSUFFICIENT_WORDS` and
    return the available count and requested count. The frontend explains
    that more curated content is needed and offers no partial session.
-   Development fixtures must contain at least 10 distinct words per
    grade to exercise both daily goals. Release content remains 50 words
    per grade (650 total).
-   If the requested review list contains duplicate, unknown,
    wrong-grade, or non-review words, reject the request with a
    validation error rather than silently substituting words.

### 7.4 Session lifecycle and resume behavior

-   A session has a `phase` of `learning` or `quiz`, and a separate
    `status` of `in_progress`, `completed`, or `abandoned`.
-   When a child selects a profile, the frontend calls
    `GET /api/v1/profiles/{profile_id}/sessions/active`. It resumes the
    returned session when the response is `200`; a `204` means there is
    no unfinished session.
-   Only one unfinished (`in_progress`) session may exist per profile.
    Enforce this in PostgreSQL with a partial unique index, not only in
    frontend logic.
-   If session creation is attempted while an unfinished session exists,
    the API returns `409` and includes the active session ID. The
    frontend retrieves and resumes that session instead of creating
    another.
-   Persist `phase` and `current_position` with
    `PATCH /api/v1/sessions/{session_id}/progress`. Position is
    zero-based.
-   During the learning phase, `current_position` identifies the
    learning card; `word_count` represents the point after the final
    learning card.
-   The child reaches the end of the learning cards and presses a visible
    **Start quiz** button. This is a distinct progress update: the client
    sends `phase: quiz` and `current_position: 0`.
-   The server accepts that transition only after it has recorded the
    child advancing through every learning card in order. Learning
    position starts at zero and may advance only one card at a time; it
    cannot jump ahead. The final advance sets `current_position` to
    `word_count`, which is the sole valid point for transition to quiz.
-   The quiz begins at position zero.
-   During the quiz phase, `current_position` is the next unanswered
    question. Answer submission advances it automatically. The frontend
    cannot skip unanswered questions or return to change a submitted
    answer.
-   The session's selected words and their order are fixed at creation.
    Refreshing or resuming never reshuffles them.
-   Either the parent or child may abandon an unfinished session using
    **Exit session** in the in-session menu; show a confirmation before
    calling the abandon endpoint. This is a usability control, not an
    authorization boundary.
-   There is no automatic expiration of unfinished sessions. They remain
    resumable until completed, explicitly abandoned, or automatically
    abandoned by a parent changing the profile's grade. Abandoned sessions
    release the profile to start another session, but their partial
    answers do not count toward mastery or add words to the review pool.
-   If a parent changes a profile's grade while a session is unfinished,
    the backend abandons that session as part of the grade update. Keep
    all previously committed mastery and review data tied to the original
    stable word IDs and grade; do not erase it. The new grade's progress
    starts independently. Switching back to a prior grade makes its
    existing progress visible again.

## 8. Quiz experience

### 8.1 Question format

The V0 quiz uses one consistent question format:

-   One question for each word in the session.
-   Every question asks the child to identify the meaning of the
    vocabulary word.
-   Four prewritten answer choices.
-   Exactly one correct answer.
-   No fill-in-the-blank, contextual, or other question formats in V0.

### 8.2 Hint behavior

-   The example sentence shown during the learning phase is available as
    an optional hint.
-   Using a hint does not prevent the child from receiving credit for a
    correct answer.
-   If the child answers correctly after using a hint, the answer counts
    as correct for the quiz score and mastery streak.
-   A correct answer after using a hint also flags the word as
    `NEEDS_REVIEW`, so it can appear again in a future session.

### 8.3 Answer submission and feedback

-   The child submits one answer for the next unanswered word in the
    fixed quiz order.
-   Each word occurs once per session and accepts one immutable answer;
    the child cannot go back and change it.
-   Show immediate correct/incorrect feedback.
-   Include a short, encouraging explanation.
-   Keep feedback age-appropriate and supportive.

### 8.4 Incorrect answers

-   An incorrect answer is recorded as missed.
-   It is flagged as `NEEDS_REVIEW`.
-   It resets the consecutive-correct mastery streak to zero.
-   The word remains eligible for later practice and may appear in a
    future session.

## 9. Mastery and review rules

### 9.1 Word states

Track each child's state for each word independently:

-   `NEW`: the child has not yet encountered the word.
-   `LEARNING`: the child has encountered the word but has not met the
    mastery requirement.
-   `MASTERED`: the child has achieved the required consecutive-correct
    streak.
-   `NEEDS_REVIEW`: a review flag indicating the word was missed or
    answered correctly only after using a hint.

`NEEDS_REVIEW` is a review flag, not a replacement for the underlying
learning/mastery state. A word may be correct for scoring or mastery
while also being flagged for review.

### 9.2 Mastery threshold

-   A word becomes `MASTERED` after three consecutive correct answers
    across three separate completed sessions. Both `daily` and `review`
    sessions count equally; each completed session can contribute at
    most one answer for a given word.
-   Mastery is committed only when the entire session is completed, not
    after each individual answer.
-   A correct answer after using a hint counts as correct toward this
    streak, but the word is also flagged `NEEDS_REVIEW`.
-   An incorrect answer resets the streak to zero when the session
    completes.
-   Answers in an unfinished or abandoned session do not change the
    committed mastery streak or review pool.
-   When the final unanswered word is submitted, the backend
    automatically completes the session and commits all of that
    session's mastery and review updates in one database transaction.

### 9.3 Review pool

-   Words answered incorrectly are added to the review pool.
-   Words answered correctly after using a hint are also added to the
    review pool.
-   A word remains in the review pool until it is answered correctly
    without using a hint in a completed session. That successful answer
    clears the review flag at session completion, whether the session is
    daily or targeted review.
-   An incorrect answer or a correct answer after using a hint keeps or
    sets the review flag. Unfinished or abandoned sessions never clear or
    add review flags.
-   V0 does not require a sophisticated interval-based spaced-repetition
    scheduler.

### 9.4 Separate dimensions of state

Implementation must keep these concepts separate: 1. **Quiz
correctness:** whether the selected answer was correct. 2. **Mastery
progress:** the consecutive-correct count across separate sessions. 3.
**Review status:** whether the word needs another look because it was
missed or a hint was used.

This separation is essential. For example, a hinted correct answer is
correct for scoring and mastery, but also needs review.

## 10. Results and progress

When the final answer is submitted, the backend automatically marks the
session completed and commits mastery/review changes. Results are
available only after this point. At the end of a quiz/session, show a
child-friendly summary that includes:

- Score or correct-answer count.
- Correct and incorrect counts.
- Words missed.
- Words answered correctly after using a hint, identified as needing review.
- A way to review the relevant words and their definitions/examples.
- A retry opportunity for words needing review.

The review pool also makes those words eligible to be selected in future
sessions.

### 10.1 Parent progress dashboard (V0)

V0 includes a lightweight parent-facing dashboard for each selected child
profile. Its purpose is to answer a small set of practical questions: Is the
child practicing consistently? How many words have they encountered and
mastered? How are they performing in quizzes? Which words need more
practice? What happened in recent sessions?

The dashboard is a read-only summary of persisted V0 learning data. It
must not introduce a separate learning system, AI analysis, or complex
reporting. Keep the child's learning screens focused on learning; make the
parent progress view a separate area reachable from the selected child's
profile/home experience.

The V0 dashboard includes:

1. **Learning activity:** completed practice days in the last 7 days and
   completed sessions by date. A day counts as a practice day when the
   child completes a session on that date; abandoned or unfinished
   sessions do not count as completed practice.
2. **Vocabulary growth:** total distinct words encountered by the child,
   plus current counts of words in `MASTERED`, `LEARNING`, and
   `NEEDS_REVIEW` states. Count each word once; `NEEDS_REVIEW` is a
   separate flag and may overlap with the underlying learning/mastery
   state, so do not add these category counts together as if they were
   mutually exclusive.
3. **Quiz performance:** aggregate correct answers, total submitted
   answers, and accuracy for the last 7 and 30 days. Calculate accuracy
   from submitted answers in completed sessions only; do not treat
   unanswered questions or abandoned sessions as incorrect.
4. **Words needing attention:** a list of the child's current review-pool
   words, showing the word and its current grade. The list is actionable
   context for the parent; targeted practice remains part of the existing
   child learning flow.
5. **Recent session history:** a simple newest-first list showing date,
   session type (`daily` or `review`), number of words, correct/incorrect
   counts, and completion status. Only completed sessions contribute to
   learning and mastery metrics; an unfinished or abandoned session may
   appear in history with its status but must not be counted as completed
   activity or quiz accuracy.

Dashboard data must be calculated from persisted profiles, sessions,
answers, quiz results, and word mastery records. The frontend must not
invent or estimate progress locally. Dashboard values must be scoped to
the selected child profile and clearly label their time windows. Empty
states should explain that progress will appear after the child completes
their first session.

**Privacy and access clarification:** V0 has no authentication or
parent-identity verification. The dashboard is a parent-oriented view,
not a secure permission boundary. It must follow the existing shared-demo
privacy warning: anyone who can reach the deployed application may be
able to view all profiles and their progress.

The V0 dashboard does not include AI-generated insights, predictive
analytics, recommendations, comparisons between children, monthly or
annual reports, data exports, or notifications. These remain future
considerations.

## 11. Data retention and privacy

-   Profiles and progress are stored in PostgreSQL through the FastAPI
    backend.
-   Keep progress until the parent deletes the child's profile or the
    demo database is reset.
-   Profile deletion uses the typed `DELETE` step and a separate final
    confirmation.
-   V0 has no account-based cloud synchronization or identity
    management.
-   Collect only the minimum child information needed for the
    experience.
-   Because authentication is intentionally absent, the profile picker
    displays every profile in the shared deployment to every visitor.
    Anyone who can reach the app/API can view or modify all profiles and
    learning data. There is no private parent/child boundary. Do not use
    real sensitive child information in a publicly reachable deployment.

## 12. Accessibility and quality expectations

### 12.1 Responsive design: desktop, tablet, and mobile

The V0 frontend must be fully responsive and adapt its layout and
interactions to desktop, tablet, and mobile screen sizes. Responsive
behavior is a V0 requirement, not a future enhancement.

- Support common desktop, tablet, and mobile viewport widths, including
  portrait and landscape orientations where applicable.
- Reflow navigation, profile selection, learning cards, quiz choices,
  results, and the parent dashboard so content remains readable and usable
  at each size.
- On narrow screens, use a mobile-appropriate layout rather than simply
  shrinking the desktop interface. Avoid horizontal scrolling for normal
  app content.
- Ensure buttons, answer choices, menus, and other interactive controls
  are comfortably usable with touch on phones and tablets, as well as with
  a mouse or keyboard on desktop.
- Preserve the same core functionality across device sizes. Do not hide
  essential learning, quiz, profile-management, or parent-dashboard
  capabilities on mobile or tablet.
- Charts, counts, tables, and session history in the parent dashboard must
  adapt to narrow screens; use stacked cards or other readable layouts
  when a wide layout would be cramped.
- Choose and document implementation breakpoints during frontend
  development. Validate the experience at representative desktop, tablet,
  and mobile viewport sizes, including at least one narrow phone viewport.
- Responsive behavior must work without requiring a separate native
  mobile application. V0 remains a responsive website; full PWA
  installation and offline support remain deferred.


-   Responsive layout for mobile, tablet, and desktop browsers.
-   Readable typography and clear visual hierarchy.
-   Large, easy-to-select answer controls.
-   Clear feedback that does not rely on color alone.
-   Keyboard-accessible controls and sensible focus behavior.
-   Appropriate contrast and age-appropriate language.
-   Handle empty states, content-loading errors, and API/database errors
    clearly.

## 13. Suggested implementation milestones

1.  **Foundation:** Lovable frontend shell, FastAPI project, PostgreSQL
    schema, Dockerfiles, and Docker Compose.
2.  **API contract and mocks:** publish `openapi.yaml`; make Lovable
    frontend mock calls conform to its request/response schemas.
3.  **Vocabulary:** prepare 50 curated words per grade, validate JSON
    content, and load it with an idempotent Python ingestion script.
4.  **Backend:** implement profile, vocabulary, session, answer,
    results, and progress endpoints.
5.  **Learning experience:** connect the frontend to the API and
    implement learning, quiz, hints, feedback, mastery, review, and
    results.
6.  **Course project quality and delivery:** unit/integration tests,
    one-command local startup, deployment, CI/CD, observability, alerting,
    and responder-agent workflow. These are course engineering-delivery
    requirements, not additional child-facing V0 product features.

7.  **Parent dashboard:** implement the agreed read-only progress view
    for each selected child profile, using persisted backend data. Include
    activity, vocabulary/mastery counts, 7- and 30-day quiz accuracy,
    words needing attention, and recent session history.
8.  **Final integration and verification:** connect the Lovable frontend
    to the implemented FastAPI endpoints, verify frontend mocks against
    the OpenAPI contract, run the acceptance checklist, and document the
    complete monorepo setup and deployment.

### 13.1 Agreed implementation approach

The product scope is sufficiently defined to move from brainstorming to
implementation. Do not add further V0 product features unless a concrete
implementation blocker requires a specification decision.

- Create a **brand-new GitHub repository** for WordWise using the
  monorepo layout in Section 5.5. Do not use the existing
  `grade-five-word-garden` repository as the base and do not modify it.
- Copy the existing Lovable-generated frontend source files from
  `grade-five-word-garden` into the new repository's `frontend/` directory.
  Treat the old repository as a source for copying frontend files only.
- Build the FastAPI backend independently in `backend/`, with PostgreSQL,
  database migrations, vocabulary ingestion, tests, and the agreed
  OpenAPI contract in the monorepo.
- Keep frontend and backend as separate applications/services even though
  they are delivered through one GitHub repository.
- Implement the agreed child learning experience and parent dashboard;
  keep the deferred enhancements in Section 17 out of V0.
- Update `openapi.yaml` when implementing dashboard data access so the
  contract explicitly supports the dashboard's required metrics and
  history. The specification defines the required behavior; endpoint
  paths and exact response schemas are technical design work and must be
  reflected in the authoritative OpenAPI file before frontend/backend
  integration.
- Design exact screen layouts during frontend implementation. The parent
  dashboard should remain a simple, separate overview for the selected
  child, not an advanced analytics experience.

### 13.2 Remaining implementation decisions (not product blockers)

The following items are intentionally left for implementation rather
than requiring more product brainstorming:

- **Dashboard UI layout:** exact arrangement, navigation entry point,
  responsive behavior, and empty-state presentation.
- **Dashboard API contract:** endpoint grouping, query parameters,
  response schemas, date/time boundaries, and aggregation implementation
  for the agreed 7-day and 30-day metrics.
- **Repository setup details:** new repository name, GitHub settings,
  branch protections, and deployment provider configuration.
- **Operational thresholds:** concrete alert thresholds and responder-agent
  behavior, to be defined while implementing the course delivery
  requirements.

These decisions must preserve the agreed V0 behavior and acceptance
criteria. If an implementation choice changes product behavior, pause
and update this specification before proceeding.

## 14. API contract (OpenAPI)

### 14.1 Source of truth

The OpenAPI 3.1 document is the authoritative contract between the
Lovable-generated frontend and the Python FastAPI backend.

-   The frontend may initially use mocked API responses.
-   Every mock request and response must conform to the OpenAPI schemas.
-   FastAPI routes, request validation, and response models must
    implement the same contract.
-   API paths are versioned under `/api/v1`.
-   The standalone machine-readable contract is `openapi.yaml` at the
    project root. Keep it synchronized with this section whenever an API
    change is made.
-   FastAPI should expose interactive documentation at `/docs`.

### 14.2 API conventions

-   JSON request and response bodies.
-   UUID identifiers for profiles, vocabulary words, and sessions; ISO
    8601 timestamps.
-   `404` for missing resources, `409` for invalid session
    state/conflicts, and `422` for request validation failures.
-   A profile can have at most one unfinished session. PostgreSQL
    enforces this with a partial unique index on active sessions.
-   A submitted answer is immutable. Each word appears at most once per
    session, and each session word can be answered once.
-   The frontend persists phase and current position through the
    progress endpoint and resumes the same word order after refresh.
-   Mastery changes are committed only when a session completes.
    Unfinished and abandoned sessions do not affect mastery streaks.
-   Profile deletion is preceded in the UI by the typed `DELETE` step
    and separate final confirmation.

### 14.3 Endpoint summary

  -------------------------------------------------------------------------------------------------
  Method                  Endpoint                                          Purpose
  ----------------------- ------------------------------------------------- -----------------------
  GET                     `/api/v1/health`                                  API health check

  GET                     `/api/v1/profiles`                                List child profiles

  POST                    `/api/v1/profiles`                                Create a child profile

  GET                     `/api/v1/profiles/{profile_id}`                   Retrieve a profile

  PUT                     `/api/v1/profiles/{profile_id}`                   Update nickname, grade,
                                                                            or daily goal

  DELETE                  `/api/v1/profiles/{profile_id}`                   Delete profile and
                                                                            associated learning
                                                                            history

  GET                     `/api/v1/grades/{grade}/words`                    Retrieve curated
                                                                            vocabulary for a grade

  GET                     `/api/v1/profiles/{profile_id}/sessions/active`   Find the profile's
                                                                            unfinished session

  POST                    `/api/v1/sessions`                                Create daily or
                                                                            targeted-review session

  GET                     `/api/v1/sessions/{session_id}`                   Retrieve/resume a
                                                                            session

  PATCH                   `/api/v1/sessions/{session_id}/progress`          Persist current phase
                                                                            and position

  POST                    `/api/v1/sessions/{session_id}/answers`           Submit the next
                                                                            immutable answer

  POST                    `/api/v1/sessions/{session_id}/abandon`           Abandon an unfinished
                                                                            session

  GET                     `/api/v1/sessions/{session_id}/results`           Retrieve completed
                                                                            session results

  GET                     `/api/v1/profiles/{profile_id}/progress`          Retrieve mastery and
                                                                            review progress
  -------------------------------------------------------------------------------------------------

### 14.4 Key request/response and lifecycle behavior

**Profile response schema:** `Profile` is a single flattened object
containing `id`, `nickname`, `grade`, `daily_goal`, `created_at`, and
`updated_at`. It does not use `allOf` with a strict `ProfileCreate`
schema, because that composition rejects the response-only fields under
`additionalProperties: false`.

**Profile selection and resume:** When a profile is selected, call
`GET /profiles/{profile_id}/sessions/active`. A `200` response returns
the active session; `204` means no active session exists. Only then
should the frontend offer a new session. A race that attempts a second
session returns `409` with `active_session_id`.

**Create daily session:** Request `profile_id`, `mode: "daily"`, and
optional `word_count` (`5` or `10`). If omitted, use the profile's daily
goal.

**Create targeted-review session:** Request `profile_id`,
`mode: "review"`, and `review_word_ids`. The list must contain 1 to 10
unique IDs from that profile's review pool. This mode supports fewer
than five words. Daily and review requests have separate schemas in the
OpenAPI `oneOf`.

**Save learning progress:** `PATCH /sessions/{session_id}/progress`
persists `phase` (`learning` or `quiz`) and `current_position`. The only
phase transition is `learning` to `quiz`. In quiz phase, the position
represents the next unanswered question; answers advance it.

**Submit answer:** Request `word_id`, `selected_option_id`, and
`hint_used`. The backend determines correctness; the client does not
submit a correctness value. The API accepts only the next unanswered
word in quiz order. Each word appears once per session, so a duplicate
answer cannot conflict with a repeated occurrence.

**Automatic completion:** When the final unanswered word is answered,
the backend marks the session `completed` automatically in the same
database transaction. The results endpoint is then available. No
separate completion call is required.

**Mastery timing:** Answer submission returns immediate correctness
feedback, but does not immediately mutate committed mastery. At session
completion, the backend applies each session answer once to that word's
streak. A correct answer (including one answered after a hint)
increments the streak; an incorrect answer resets it. A hinted correct
answer also flags the word for review. Unfinished or abandoned sessions
do not affect mastery or review state.

**Abandon:** `POST /sessions/{session_id}/abandon` marks an unfinished
session abandoned and releases the profile to start another session.
Partial answers remain as session history but are not applied to
mastery.

**Demo-only answer choices:** The V0 mock/session response may include
`is_correct` on options to simplify mock UI behavior. This is not
production-safe. A production quiz API should keep the correct answer
server-side and reveal it only after answer submission.

### 14.5 Machine-readable contract

The standalone `openapi.yaml` file defines paths, operations,
request/response schemas, errors, and examples. Use it for frontend mock
tooling and backend contract tests.

## 15. Decisions register

  -----------------------------------------------------------------------
  Topic                   V0 decision             Status
  ----------------------- ----------------------- -----------------------
  Product                 WordWise vocabulary app Agreed
                          for K--12               

  Platform                Responsive website      Agreed

  Accounts                No accounts or login    Agreed

  Backend                 Python FastAPI REST API Agreed

  Database                PostgreSQL              Agreed

  Runtime                 Docker Compose          Agreed

  API contract            OpenAPI 3.1 is the      Agreed
                          frontend/backend source 
                          of truth                

  Frontend                Lovable-generated UI;   Agreed
                          mock API calls first    

  Repository              New WordWise monorepo;  Agreed
                          copy existing Lovable
                          files into frontend/

  Parent dashboard        Separate read-only      Agreed
                          progress view per child

  Dashboard API           Extend OpenAPI during   Implementation
                          dashboard implementation follow-up

  Account management      Explicitly excluded     Agreed

  Persistence             PostgreSQL via backend  Agreed

  Child profiles          Multiple profiles on    Agreed
                          one browser/device      

  Profile fields          Nickname, grade, daily  Agreed
                          goal                    

  Daily goal              Parent chooses 5 or 10  Agreed
                          words                   

  Grade range             Kindergarten--Grade 12  Agreed

  Content volume          50 curated words per    Agreed
                          grade                   

  Content delivery        Grade-specific content  Agreed direction
                          loading                 

  Learning layout         One word per            Agreed
                          screen/card             

  Learning content        Definition and example  Agreed
                          sentence                

  Syllables               Text syllable breakdown Agreed
                          in V0                   

  Progress indicator      Visual bar plus numeric Agreed
                          count                   

  Quiz format             Meaning recognition,    Agreed
                          four choices, one       
                          correct                 

  Hint                    Example sentence from   Agreed
                          learning screen         

  Hint scoring            Correct after hint      Agreed
                          counts as correct       

  Hint review             Correct after hint is   Agreed
                          also flagged for review 

  Incorrect answer        Missed, flagged for     Agreed
                          review, streak reset    

  Feedback                Immediate, with short   Agreed
                          explanation             

  Answer changes          Submitted answer is     Agreed
                          final                   

  Mastery                 Three consecutive       Agreed
                          correct answers across  
                          separate sessions       

  Review selection        Missed and hinted words Agreed
                          eligible in later       
                          sessions                

  Progress retention      Until profile deletion  Agreed
                          or demo database reset  

  Deletion safeguard      Exact uppercase         Agreed
                          `DELETE`, then final
                          confirmation; permanent   

  PWA/offline             Deferred; not promised  Agreed
                          in V0                   

  Audio pronunciation     Deferred                Future

  Advanced spaced         Deferred                Future
  repetition                                      

  Daily selection         Review, learning, new,   Agreed
                          mastered; deterministic
                          tie-breaking          

  Exact screen layouts    To be designed during   Open
                          implementation          

  Quiz back-navigation    No changing an answer   Agreed
                          after submission        
  -----------------------------------------------------------------------


## 17. Future product directions (not part of V0)

### 17.1 Within-grade proficiency levels and diagnostic placement

**Problem to solve:** A student's school grade does not necessarily indicate
their current vocabulary proficiency. Two students in Grade 4 may have very
different vocabulary knowledge. WordWise should eventually assess a
student's starting point within the grade and build a learning path from
that point, rather than assuming every student is ready for the same
Grade 4 content.

**Proposed direction:** Introduce multiple proficiency levels within each
grade (for example, Grade 4 Level 1, Level 2, and Level 3). The number and
names of levels are intentionally undecided. A short diagnostic assessment
would estimate the student's starting level, after which WordWise would
recommend appropriately challenging vocabulary and progressively build
knowledge.

Potential future capabilities:

-   **Diagnostic placement:** On first use of a grade, assess a sample of
    vocabulary across its levels and use the results to recommend a starting
    level. Do not infer proficiency from grade alone.
-   **Progressive learning path:** Begin at the recommended level and
    introduce more challenging vocabulary as the student demonstrates
    readiness.
-   **Evidence-based advancement:** Move a student between levels based
    on performance across multiple words and sessions, not a single
    question or quiz.
-   **Ongoing reassessment:** Revisit placement as the student's knowledge
    grows, allowing the system to adjust difficulty when content is too
    easy or too difficult.
-   **Separate grade and proficiency:** Keep the student's school grade
    (K–12) distinct from their vocabulary proficiency level within that
    grade. A Grade 4 student might begin below, at, or above the expected
    Grade 4 starting point.

This is a future product direction only. It does not change V0's current
model of one curated vocabulary pool per grade, its 50-word-per-grade
content target, its session selection rules, or its API contract. Before
implementation, define the level framework, diagnostic question design,
placement thresholds, advancement criteria, and how progress is handled
when a student changes grade.

### 17.2 Enhanced parent insights and analytics

The V0 parent dashboard provides factual activity, vocabulary, quiz, review,
and session-history summaries. Future versions may build on that foundation
with richer interpretation and reporting, once there is evidence that parents
need it.

Potential future capabilities:

- AI-generated plain-language learning summaries and observations.
- Personalized recommendations for what a parent or child could practice
  next.
- Longer-term trends, including monthly and term-based progress views.
- Downloadable or shareable progress reports.
- Optional reminders or progress notifications.
- Carefully designed comparisons across a parent's own child profiles,
  without public rankings or pressure-based competition.

These enhancements are not part of V0. Any future AI-generated insight must
be grounded in the child's recorded learning data, explain uncertainty, and
avoid presenting quiz accuracy as proof of long-term retention.

### 17.3 Book-specific vocabulary packs

**Concept:** Offer optional vocabulary packs built around well-known books
or book series. For example, after reading *Harry Potter*, a student could
choose or purchase a *Harry Potter* vocabulary pack containing words drawn
from the books. The goal is to reinforce vocabulary encountered while
reading and help students understand and retain those words in context.

Potential future capabilities:

- **Book-based word collections:** Curate vocabulary that appears in a
  particular book or series, with age/reading-level guidance where
  appropriate.
- **Contextual learning:** Teach each word using an original definition,
  age-appropriate example, and an explanation of how the word is used in
  the story. Avoid reproducing copyrighted passages from the book.
- **Optional packs:** Let families browse, preview, and optionally purchase
  packs independently of the standard grade-based vocabulary experience.
- **Progress tracking:** Track learning and mastery of book-pack words
  separately while allowing them to contribute to the student's overall
  vocabulary progress where appropriate.
- **Reading connection:** Allow a student to select a book they have read
  and use its vocabulary pack as a reinforcement activity.

Important considerations before implementation:

- **Content rights:** Names of books and series may be used to identify a
  pack, but reproducing book text, passages, or substantial expressive
  content may require permission or licensing. Prefer original definitions
  and examples unless appropriate rights have been secured.
- **Age appropriateness:** Establish suitable age/grade guidance and avoid
  assuming every student in a school grade is ready for the book's content.
- **Pack design:** Decide whether packs are organized by individual book,
  series, reading level, or a combination.
- **Commercial model:** Define whether packs are free, individually
  purchased, bundled, or offered through a subscription before building
  payment functionality.
- **Quality control:** Curate and review word selection so packs teach
  useful vocabulary rather than simply listing every unfamiliar word.

This is a future product direction only. It does not change V0's curated
50-word-per-grade content, grade-based session selection, or API contract.
No book packs, purchasing, or payment processing are included in V0.

## 16. Implementation acceptance checklist

V0 is ready for release when the following are verified:

-   [ ] Parent can create, edit, select, and delete multiple child
    profiles.
-   [ ] Profile creation requires only nickname (1–20 characters), grade, and daily goal.
-   [ ] The profile picker lists all profiles in the shared demo instance; no profile is private.
-   [ ] Profile deletion requires exact uppercase `DELETE` and a separate
    confirmation; deletion is permanent and has no undo.
-   [ ] Each profile can be assigned a grade from Kindergarten through
    Grade 12.
-   [ ] Parent can set a daily goal of 5 or 10 words.
-   [ ] The app loads the selected grade's curated vocabulary content.
-   [ ] A learning card shows one word, definition, example, syllables,
    and progress.
-   [ ] A quiz has one meaning question per session word and four
    options per question.
-   [ ] The example sentence can be used as an optional hint.
-   [ ] A correct answer after a hint counts as correct and is flagged
    for review.
-   [ ] An incorrect answer is marked missed, flagged for review, and
    resets the streak.
-   [ ] Feedback appears immediately after each answer.
-   [ ] A submitted answer cannot be changed.
-   [ ] Mastery requires three consecutive correct answers across three
    separate sessions.
-   [ ] Review flags clear only after a correct answer without a hint in a completed session.
-   [ ] Daily selection follows the documented deterministic priority and tie-break rules.
-   [ ] Daily sessions contain exactly 5 or 10 distinct words; insufficient content returns 409 without creating a partial session.
-   [ ] Both daily and review sessions count toward the three-session mastery streak.
-   [ ] Session progress survives a browser refresh when the backend and
    PostgreSQL are available.
-   [ ] Results show score/counts and identify missed and hinted words.
-   [ ] Parent can open a separate progress view for a selected child profile.
-   [ ] Dashboard shows completed practice days in the last 7 days.
-   [ ] Dashboard shows distinct words encountered and current mastered,
    learning, and review counts without double-counting review flags.
-   [ ] Dashboard shows quiz accuracy for the last 7 and 30 days using
    submitted answers from completed sessions only.
-   [ ] Dashboard lists the child's current words needing review.
-   [ ] Dashboard shows recent session history with date, session type,
    word count, results, and status.
-   [ ] Dashboard metrics are derived from persisted backend data and
    scoped to the selected child profile.
-   [ ] Dashboard empty states are clear before the first completed session.
-   [ ] The UI does not imply that parent views are private or protected
    by authentication in the shared demo deployment.
-   [ ] API/database/content errors are handled honestly and clearly.
-   [ ] The frontend adapts cleanly to desktop, tablet, and mobile viewport sizes.
-   [ ] Core profile, learning, quiz, results, and parent-dashboard features remain usable across supported device sizes.
-   [ ] Normal app content does not require horizontal scrolling on narrow mobile screens.
-   [ ] Touch controls are comfortably usable on phones and tablets.
-   [ ] Responsive layouts are verified at representative desktop, tablet, and narrow-phone viewport sizes.
-   [ ] Frontend mock responses conform to the OpenAPI contract.
-   [ ] The application starts with Docker Compose and PostgreSQL data
    persists across container restarts.
-   [ ] Profile response schema validates the full profile object,
    including ID and timestamps.
-   [ ] Selecting a profile retrieves and resumes its unfinished session
    when one exists.
-   [ ] PostgreSQL prevents more than one in-progress session per
    profile.
-   [ ] Learning phase and current card position survive refresh.
-   [ ] The server enforces sequential learning-card progression and only allows quiz transition after all cards are viewed.
-   [ ] Previously submitted answer feedback, including explanation and correct option, can be restored after refresh.
-   [ ] Changing grade abandons any active session but preserves mastery data associated with the original grade.
-   [ ] Targeted review can create sessions containing 1 to 10 unique
    review words.
-   [ ] A session contains no repeated vocabulary word IDs.
-   [ ] The final submitted answer automatically completes the session.
-   [ ] Mastery and review updates are committed only when a session
    completes; unfinished/abandoned sessions do not count.
-   [ ] The app does not claim offline capability in V0.

------------------------------------------------------------------------

**Specification note:** This document consolidates the decisions made
during product brainstorming. Where a detail was not explicitly
finalized, it is marked as an implementation direction or open item
rather than presented as a confirmed requirement.
