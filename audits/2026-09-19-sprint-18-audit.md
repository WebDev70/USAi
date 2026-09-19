# Audit Report: Sprint 18 (2026-09-19)

## 1. Executive Summary

This audit provides a comprehensive, read-only review of the USAi Chat repository as of 2026-09-19. The analysis covered the canonical backlog (`backlog.md`), the repository's Git state, governance scripts, specification files, and the non-authoritative Obsidian backlog mirror.

**Key Finding:** The project is in a high-risk state. The `main` branch is non-functional on a fresh clone, and the current working tree contains a significant regression in a critical governance script (`doc-consistency-check.sh`) that would be deployed if a commit were made from the current state. Backlog and specification hygiene is inconsistent, violating established project governance.

While the core application architecture appears sound, the immediate priority must be to restore repository health and enforce existing governance rules before any new feature work is undertaken.

## 2. Key Findings & Evidence

This section details the specific issues uncovered during the audit, supported by direct evidence from the repository.

*   **Finding 2.1: Critical Governance Regression (#87)**

    *   **Description:** A critical governance script, `scripts/doc-consistency-check.sh`, has been "silently weakened" in the current working tree. This script is designed to prevent documentation drift by ensuring that key principles and conventions are defined in a single canonical file and linked to elsewhere, not duplicated.
    *   **Evidence:** A `git diff HEAD` on the script reveals that its scope has been drastically reduced. The original version scanned 15 files, including all 12 `.clinerules` files. The modified version scans only 3 files and completely ignores the `.clinerules` directory. This effectively disables the guardrail for the entire Cline agentic workflow.
    *   **Supporting Evidence:** The tests for this script in `backend/tests/python/test_scripts.py` have also been modified in the working tree to remove test cases that would have failed with the weakened script, hiding the regression from the test suite.
    *   **Impact:** This change represents a severe regression. It allows core architectural and process documentation to become inconsistent without detection, undermining the "RAIL" development process. Committing the working tree in its current state would ship this regression.
    *   **Code Diff:**
        ```diff
        --- a/scripts/doc-consistency-check.sh
        +++ b/scripts/doc-consistency-check.sh
        @@ -28,13 +28,8 @@
         # .clinerules/rail-pipeline.md, and the harness tooling guides.  These should LINK to the
         # canonical source, not copy it.
         # ...
        -ENFORCING_FILES=(
        -    "AGENTS.md"
        -    ".clinerules/rail-pipeline.md"
        -    "docs/tooling/cline.md"
        -    "docs/tooling/continue.md"
        -)
        +ENFORCING_FILES=""
        +if [ -f "$REPO_ROOT/AGENTS.md" ]; then
        +    ENFORCING_FILES="$REPO_ROOT/AGENTS.md"
        +fi
        +for scan_dir in "$REPO_ROOT/.roo" "$REPO_ROOT/docs/tooling"; do
        ```
*   **Finding 2.2: Unstable `main` Branch & Dirty Working Tree (#76)**

    *   **Description:** The `main` branch is unstable and the current working directory is "dirty," containing a large number of uncommitted changes. The project fails its own test suite on a fresh checkout of the `main` branch head, and the working tree contains approximately 68 modified files.
    *   **Evidence:**
        *   `git status --porcelain` shows a large number of modified, deleted, and untracked files.
        *   The Obsidian memory notes (`2026-09-18-200500-backlog-grooming-pass.md`) explicitly state: "I never checked whether `main` actually builds... a fresh clone of `main` HEAD (`7e25ee5`) ... `./run-tests.sh` -> **exit 1**".
    *   **Impact:** The repository is not in a shippable state. The `main` branch, which should be a stable foundation, is broken. The dirty working tree makes it impossible to isolate changes or confidently start new work. This directly violates basic software development best practices.
*   **Finding 2.3: Systemic DoD Violations in Specifications**

    *   **Description:** There is a widespread failure to adhere to the project's "Definition of Done" (DoD) as defined in `docs/governance.md`. This rule requires that when a backlog item is completed, its corresponding specification file in `docs/specs/` must have its `Status:` header updated to `Done`.
    *   **Evidence:** A search of the `docs/specs/` directory for `**Status:**` revealed numerous specification files for items marked as complete in `backlog.md` that are still listed as `In Progress` or `Ready`. Examples include `docs/specs/more-file-types.md`, `docs/specs/log-file-viewer.md`, and `docs/specs/streaming-tool-calling.md`.
    *   **Impact:** This failure to follow process creates a disconnect between the stated status of work in the backlog and the documented status in the specifications. It leads to confusion, makes it difficult to trust the project's documentation, and indicates a breakdown in process discipline.
*   **Finding 2.4: Inconsistent Backlog Hygiene**

    *   **Description:** The canonical `backlog.md` file suffers from several structural inconsistencies and hygiene issues that reduce its clarity and reliability as a planning document.
    *   **Evidence:**
        *   **Malformed Entry:** A backlog item at line 717 is malformed, lacking a proper ID and checkbox (`** *(S)* — Done...`). This is likely a corrupted entry for what should have been `#49`.
        *   **Misplaced Item:** Item `#57` (an open item) is incorrectly located within the `## Completed / Archive` section.
        *   **Non-Standard ID:** Item `#48b` uses a non-standard alphanumeric ID, breaking the numeric sequence.
        *   **Stale Commentary:** The grooming notes contain stale or contradictory information, such as claiming "No items are blocking" in a section that then details a blocking item (`#76`).
    *   **Impact:** These inconsistencies make the backlog difficult to parse automatically and create confusion for human readers. They suggest that backlog grooming is not being performed with sufficient rigor.
*   **Finding 2.5: Divergent Backlog Purposes (Canonical vs. Mirror)**

    *   **Description:** The canonical `backlog.md` in the repository and the `product-backlog.md` in the Obsidian vault serve different purposes, leading to significant structural and content differences.
    *   **Evidence:** The repository `backlog.md` is a long, detailed ledger organized by sprints and findings. The Obsidian mirror is a much shorter, topic-oriented document that summarizes the backlog and contains richer, more up-to-date grooming notes, priorities, and sprint proposals (e.g., the analysis of blocking issue `#87` is far more detailed in the mirror).
    *   **Impact:** Recognizing this distinction is key to understanding the project's workflow. The Obsidian mirror appears to be the primary tool for active planning and grooming, while the repository backlog serves as the engineering source of truth. The risk is not so much in the divergence itself, but in the potential for them to become completely desynchronized on critical items, which does not appear to be the case currently.

## 3. Risks & Prioritized Recommendations

This section analyzes the impact of the findings and proposes a concrete, prioritized action plan.

*   **Risk 3.1: High**
*   **Recommendation 3.1 (P0):**
*   **Recommendation 3.2 (P1):**
*   **Recommendation 3.3 (P2):**
