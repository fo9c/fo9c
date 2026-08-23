# GitHub profile migration checklist

Target account: `fo9c3a`  
Legacy account: `fo9c`

## Profile repository

1. On `fo9c3a`, create a **public** repository named exactly `fo9c3a`.
2. Push this repository's `README.md` to its default branch.
3. Confirm that the README appears on `https://github.com/fo9c3a`.

## Public repositories found on the legacy profile

- `fo9c/fo9c` — original profile repository.
- `fo9c/fo9c.github.io` — personal website repository.

For each repository, prefer a full Git mirror so branches, tags and commit history are preserved:

```bash
git clone --mirror https://github.com/fo9c/REPOSITORY.git
cd REPOSITORY.git
git push --mirror https://github.com/fo9c3a/REPOSITORY.git
```

Create the empty destination repository under `fo9c3a` before the push. Replace `REPOSITORY` with the actual repository name. Do not add secrets or copy private configuration into a new public repository.

## Items intentionally removed from the old profile

- Visitor counter: depends on a third-party counter and carries old-account state.
- WakaTime card: its link targeted the README itself and no verified WakaTime identity was available.
- Spotify card: requires a separate deployment or authorization and was not verifiable.
- Trophy wall and multiple statistics cards: noisy on an empty new account and depend on several external services.
- Automated refresh timestamp: displayed a stale 2024 date without a working workflow.
- Large text-art block: rendered poorly on narrow screens.

## Post-migration checks

- Replace legacy links in `README.md` only after each destination repository exists.
- Review repository descriptions, home-page URLs, Actions secrets and Pages settings separately.
- Re-enable GitHub Pages for `fo9c3a.github.io` after checking its source for hard-coded `fo9c` URLs.
- Do not claim that stars, followers, issues or pull requests were migrated; those are GitHub account-level data.

