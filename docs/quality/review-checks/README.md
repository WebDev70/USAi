# USAi QA Review Checks

This directory contains the canonical, tool-neutral review criteria for the USAi
Chat project. These checks are applied during the QA Review step of the RAIL
pipeline to ensure quality, consistency, and completeness.

Scripts and tools MUST read this manifest or a shell array pointing to these files;
they must not depend on any harness-specific configuration like `.continue/` or
`.clinerules/`.

## Review Sequence

The checks are designed to be applied in a logical sequence, from initial readiness
to final completion.

| Order | Check File | Purpose |
|---|---|---|
| 1. | [`definition-of-ready.md`](./definition-of-ready.md) | **Start Gate:** Confirms a feature is well-defined and ready for development. |
| 2. | [`code-quality-review.md`](./code-quality-review.md) | Enforces project coding conventions and patterns. |
| 3. | [`test-coverage.md`](./test-coverage.md) | Ensures new logic is tested and coverage gates pass. |
| 4. | [`security-review.md`](./security-review.md) | Catches common security vulnerabilities like secret leaks. |
| 5. | [`dependency-and-supply-chain-review.md`](./dependency-and-supply-chain-review.md) | Maintains a minimal and audited runtime dependency surface. |
| 6. | [`iac-review.md`](./iac-review.md) | Keeps environment configuration declarative and reproducible. |
| 7. | [`ui-ux-review.md`](./ui-ux-review.md) | Maintains frontend quality, accessibility, and responsiveness. |
| 8. | [`docs-in-sync.md`](./docs-in-sync.md) | Ensures documentation is updated with the code. |
| 9. | [`acceptance-criteria.md`](./acceptance-criteria.md) | **End Gate:** Verifies the feature meets its stated goals. |
| 10. | [`definition-of-done.md`](./definition-of-done.md) | **Meta-Gate:** The final check asserting all other gates have passed. |
