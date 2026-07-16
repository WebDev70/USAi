# Housekeeping Checklist

Use per task for lightweight cleanup and periodically for a deeper sweep.

## Per-task leave-no-trace gate

- [ ] No accidental scratch files are included.
- [ ] No temporary files are included.
- [ ] No stale TODO/FIXME/HACK comments were introduced without tracking.
- [ ] Spec/task status is updated.
- [ ] Trace and scorecard are updated for non-trivial work.
- [ ] Follow-up log/backlog is updated for deferred items.
- [ ] Prompt, data, and eval artifacts are versioned or dated when needed.

## Periodic sweep

- [ ] Specs/tasks match completed work.
- [ ] Follow-up log has owners/statuses.
- [ ] Old advisory gaps are reviewed.
- [ ] Data folders do not contain unapproved secrets or sensitive data.
- [ ] Processed data still traces back to raw sources.
- [ ] Prompt files have metadata and related evals.
- [ ] Scorecards are completed for recent non-trivial work.
- [ ] Tool inventory is current.
- [ ] Dependency/tool versions are reviewed.

## Blocking failures

- Secret or credential found in project artifacts.
- Completed work has no evidence trace.
- Deferred blocking gap is incorrectly marked advisory.
