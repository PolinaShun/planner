# Project Instructions: Senior Planner Polina (v2.1)

## UI & Visual Standards
- **Theme:** Smoky Green. Background: `#1e2b24`, Accents: `#8da399` (Sage) and `#d4a5a5` (Rose).
- **Style:** Glassmorphism (blur: 20px-30px, semi-transparent backgrounds `rgba(255,255,255,0.05)`).
- **Sidebar:** Always fixed at 180px width. No hover expansion.
- **Tasks Page:** All active tasks must be in ONE single block titled "ВСЕ ЗАДАЧИ" (no split between Today/Personal/Dreams).
- **Progress Page:** Unified dashboard. Top: Trackers (Body, Study, Clients). Bottom: Analytics (Weight, Monthly Progress, Archive Grid, Productivity).
- **Study Widget:** Unified "УЧЕБА" block containing all sub-trackers (Freud, etc.) sequentially.
- **Full Calendar:** A dedicated full-screen view showing task names inside date cells.

## Core Logic & Data
- **Morning Greeting:** Must ALWAYS include a reminder to "хорошо позавтракать" and "сделать упражнения".
- **Body Metrics:** Parameters (Weight, Waist, Hips, Chest) must be displayed in a 2-column grid with high contrast (Sage/White).
- **Analytics:** 
    - Weight chart starts from 2026-01-01.
    - Monthly progress highlights the current month in Rose.
    - Archive grid shows the previous month's actual history (e.g., April 18/30).

## Workflow: Mandatory Testing
- **Mandatory Sub-agent Verification:** BEFORE delivering any changes, a sub-agent MUST be invoked to test functionality.
- **Test Protocol:** Use `TEST_PROTOCOL.md` for verification scenarios.
- **Stability:** No alert() popups for errors; use console.error for silent logging.
- **Database:** Copy `planner_export_*.db` from Downloads to `backups/` with a timestamp.
