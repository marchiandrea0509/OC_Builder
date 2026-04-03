# Workspace Git sync

Use this reference when a project workspace should be protected by periodic Git checkpointing.

## Goals

- keep each real workspace in its own repository
- keep sync conservative and non-destructive
- commit and push only when the repo is in a safe state
- keep failure reporting concise
- keep indexing separate from Git sync

## Recommended policy

- one repository per workspace
- one `origin` remote per workspace
- periodic sync every 12 hours unless a project needs tighter checkpoints
- commit only when there are working-tree changes
- fetch before pushing
- refuse auto-push when the branch is behind or diverged
- refuse auto-push during merge/rebase/cherry-pick states
- report only when attention is needed

## What Git sync should do

1. verify the path exists
2. verify the path is a Git repo
3. verify `origin` exists
4. verify there is no in-progress Git operation
5. fetch `origin`
6. determine current branch and upstream state
7. if the branch is behind or diverged, stop and report
8. if there are changes, commit them with a predictable message
9. push when safe

## What Git sync should not do

- do not auto-resolve merge conflicts
- do not auto-rebase
- do not force-push
- do not push if the branch is behind or diverged
- do not fold indexing into the sync job

## Indexing

Keep indexing separate.

Reason:
- OpenClaw memory indexing/search sync already has its own mechanism (`memorySearch.sync.watch`)
- Git sync is backup/versioning
- indexing is retrieval/embeddings/state freshness

If indexing health needs monitoring later, add a separate health check instead of coupling it to Git sync.

## Reusable resources

- `scripts/setup_git_sync_targets.py` — initialize missing repos, set/update `origin`, set local Git identity if missing
- `scripts/git_sync_workspaces.py` — safe periodic commit/push runner
- `assets/workspace_git_sync.targets.template.json` — template for future workspace target lists
