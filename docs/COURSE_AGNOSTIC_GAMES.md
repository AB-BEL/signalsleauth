# Course-agnostic games (no fixed textbook)

Signal Sleuth is a **platform**. Chapter content is **not hard-wired** to one book.

## How to adapt for another course
1. Admin → **Chapter management** — set titles (e.g. “Unit 1: Markets”).
2. Admin → **Question management** — add questions/rubrics for that course, **or**
3. Admin → **Game management** — upload a self-contained **HTML** file per chapter.

HTML games are designed **independently** (any editor). Requirements:
- Call `SignalSleuthGame.submitScore({ level_num, answers: [...] })` after scoring UI.
- Levels 1–7; answers scored on the **server** from the question bank when present.
- See `uploads/BLANK_CHAPTER_TEMPLATE.html` and `uploads/GAME_INTEGRATION_SNIPPET.html`.

## Updates
- Change code in Git → redeploy free host.
- Change content → re-upload HTML or edit question bank (no code deploy needed).

## Withdraw / take offline
You control the free-host account. Suspend or delete the web service anytime (see FREE_HOSTING_AND_WITHDRAWAL.md).
