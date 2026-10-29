# Custom Workspaces Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline and one fresh final reviewer.

**Goal:** User-owned per-screen layouts with safe selective reuse across the app.

**Architecture:** workspace_layouts.py validates/persists exact and portable layouts; ui/workspaces.py supplies dock hosts, toolbar editing and management dialog; ui/workspace_setup.py adapts existing screens without replacing their data controls.

**Tech Stack:** Python, Qt QMainWindow/QDockWidget/QToolBar, atomic JSON persistence.

**Spec:** docs/superpowers/specs/2026-10-29-custom-workspaces.md

## Constraints
- Stay on main and push as already requested. No document/project changes from layout operations.
- Preserve screen indices and existing controls, shortcut bindings and Word ownership.
- Independent layouts, shared-role copying only, recoverable defaults, display-safe floats.

## Review focus
- Corrupt profile/state: reject or recover defaults without startup failure.
- Copy between different screens: retain incompatible tools and panels.
- Switching/closing while floating: hide inactive floats, restore intended visibility, close owned Word cleanly.
- Reset/lock: restore usability including hidden panels/toolbars; editing mode recoverable through main View menu.
- Repeated startup/resize/navigation: persistence does not mutate projects or propagate unintended changes.

### Task 1 — Layout model
- [x] Add failing tests for validated persistence, exact independence and compatible copying.
- [x] Implement workspace_layouts.py and prove tests pass.
### Task 2 — Native workspace and editor
- [x] Add failing Qt tests for dock/float/hide/lock/reset, named layouts and toolbar order.
- [x] Implement workspaces.py with safe restore/copy, appearance controls and management dialog.
### Task 3 — Integration
- [x] Adapt capture/editor/document/review/libraries; expose workspace controls on every screen.
- [x] Verify lifecycle and existing workflows, minimum-size/theme rendering, frozen startup and native Word smoke.
- [x] Update help/docs and independent review. Full suite: 218 passed; build and packaged verification exit 0.
- Integration: commit and push directly to main as requested.

## Ledger
Executing inline; retain existing business controls to avoid changing capture/annotation/document semantics. Cross-screen role matching deliberately skips content and screen-specific tools. Exact Qt dock state is only reused on its originating screen; copied/named cross-screen layouts use portable roles.

Review/verification rulings: remove duplicate default action rows but retain them as an optional Screen actions panel; keep headers outside the central dock region; keep approval controls outside the scroll area at minimum size; give review a Choose/Review/Finalise strip; isolate QA preferences from user layouts. Save the source action catalogue so hidden shared actions copy correctly while destination-only actions remain. Toolbar catalogues are scoped to compatible screen commands. Preference-write errors report status without blocking navigation. Frozen smoke exercises Word editor floating/navigation and authored document preservation.
