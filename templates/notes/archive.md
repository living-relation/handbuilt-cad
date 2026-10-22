# _archive (parts home)

Owner: handbuilt-cad layout (setup.sh). Agent note.

- `<job>/`: iteration history, superseded script versions, alternate copies and other items kept only for reference. Nothing here is used by a build.
- `backup-<date>/`: hash-backed tar backups (`*.tar` + `*.sha256` + per-file hash lists) taken before cleanups or moves.
- `git-history-<date>/`: `git bundle` files (full history of retired clones) and saved uncommitted diffs. Restore with `git clone <file>.bundle`.
- Safe to prune: delete what is no longer needed (oldest backups first). Check `../MANIFEST.sha256` first if a file's origin matters.
