# Before this repo goes public

1. `gitleaks git --redact` over the full history: 0 findings (or each one reviewed and allow-listed with a reason).
2. TruffleHog over the full history: 0 verified findings.
3. Home-path scan: `git grep -nE '/home/[a-z]+/|C:[\\/]Users[\\/]'` is empty, then create `.guard-strict` so the hook blocks new ones.
4. No part/model files anywhere in history: `git rev-list --objects --all` has no STEP/STL/3MF/F3D/PLY/OBJ/IGES/BREP/GLB/NPZ/NPY/ZIP (Claude skill zips at `skills/<name>.zip` are the only zip exception).
5. No personal data in commit metadata: every author/committer email is a noreply address.
6. Part build scripts and specs reviewed for third-party (OEM-derived) dimensions.
7. All of the above recorded in the PR that flips visibility.
