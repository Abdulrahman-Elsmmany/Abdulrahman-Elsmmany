# Profile Repo Setup

This folder is the contents of your special profile repo at `Abdulrahman-Elsmmany/Abdulrahman-Elsmmany`. Push these files to that repo and the README will auto-update daily from your GitHub data — no blog or external feed required.

## What's in this folder

```
profile-repo/
├── README.md                                    # the v2 profile README
├── build_readme.py                              # Python script — releases + activity
├── requirements.txt                             # pip deps (just `requests`)
├── SETUP.md                                     # this file
└── .github/
    └── workflows/
        ├── build.yml                            # daily auto-update workflow
        └── blog-post-workflow.yml.template      # rename to .yml when you have RSS
```

## First-time push (10 minutes)

### 1. Create the profile repo

If you don't already have it: go to GitHub → New repo → name it **`Abdulrahman-Elsmmany`** (must match your username exactly) → make it public → don't initialize with a README. GitHub auto-detects this as your "special" profile repo.

### 2. Push these files

From a local clone of this folder:

```bash
cd profile-repo
git init
git add .
git commit -m "Initial profile README + auto-update workflow"
git branch -M main
git remote add origin https://github.com/Abdulrahman-Elsmmany/Abdulrahman-Elsmmany.git
git push -u origin main
```

If the repo already exists with content (e.g. your old README), back up the old one first, then force-push:

```bash
git push -u origin main --force
```

### 3. Trigger the first workflow run

Go to your repo on GitHub → **Actions** tab → click the **"Build README"** workflow on the left → **"Run workflow"** button on the right → click the green confirm button.

First run takes ~30–45 seconds. When it finishes, refresh your profile (`github.com/Abdulrahman-Elsmmany`) and the **Recent releases** + **Recently active** sections will be populated. The placeholder text disappears.

### 4. Verify the badge turns green

The **Build README** badge in the README footer should now render green. If it's red, click it to see the workflow run logs and find the error.

## How it works

The workflow runs daily at 06:30 UTC (configurable in `build.yml`). It:

1. Checks out the repo
2. Installs `requests`
3. Runs `build_readme.py`, which:
   - Hits the GitHub GraphQL API once to pull all your public, non-fork repos
   - Builds two markdown lists — recent releases (across all repos) and recently active repos (sorted by last commit)
   - Replaces the content between the `<!-- recent_releases starts -->` ... `<!-- ends -->` and `<!-- recent_activity starts -->` ... `<!-- ends -->` markers in `README.md`
4. Commits and pushes — but only if the rendered content actually changed (no empty commits polluting your contribution graph)

It uses the default `GITHUB_TOKEN` that's automatically available inside Actions — no Personal Access Token needed for public data.

## When you have a blog (later)

When you have an RSS-enabled blog (Substack, dev.to, Medium, your personal site), you can add a "Recent writing" column:

1. Rename `.github/workflows/blog-post-workflow.yml.template` → `.github/workflows/blog-post-workflow.yml`
2. Edit the `feed_list:` line in that file to point at your real RSS URL
3. In `README.md`, change the `<table>` inside `#### Latest` from two columns (50% / 50%) to three columns (33% / 33% / 33%) and add a third `<td>` for blog posts:

```html
<td valign="top" width="33%">

##### Recent writing
<!-- BLOG-POST-LIST:START -->
- _Workflow hasn't run yet._
<!-- BLOG-POST-LIST:END -->

</td>
```

4. Commit and push. Both workflows now run daily.

## Customization

- **Run more / less often** — edit the `cron:` line in `.github/workflows/build.yml`. Standard 5-field cron syntax. Daily at 06:30 UTC = `"30 6 * * *"`. Twice a day = `"30 6,18 * * *"`. Hourly = `"0 * * * *"`.
- **Show more / fewer items** — edit `limit: int = 5` in the `build_releases` and `build_activity` calls in `build_readme.py`.
- **Filter out specific repos** — add a `SKIP_REPOS = {"name1", "name2"}` set in `build_readme.py` and check against it in `build_activity`.
- **Change the relative-date format** — edit `format_relative()` in `build_readme.py`. The output is sortable strings like `2d ago`, `1w ago`, `3mo ago`, `1y ago`.

## Troubleshooting

**The badge stays red.** Click it → look at the failed workflow run → expand the failed step. Most common causes:
- The repo was created without `Actions write` permission. Fix: Settings → Actions → General → Workflow permissions → "Read and write permissions" → Save.
- The Python script raised an exception. The error output is in the **Build README** step.

**The README didn't change after the workflow ran successfully.** Two reasons this is fine:
- The script is idempotent — it only commits when the rendered content changes. If nothing new shipped, nothing new appears.
- You may have no tagged releases yet. The script falls back gracefully to "No tagged releases yet" — that's expected if your repos haven't been tagged with `v0.1.0`-style versions yet.

**I want a Personal Access Token instead of the default token.** You don't need one — the default `GITHUB_TOKEN` works for all public data via GraphQL. You'd only need a PAT if you want to surface private-repo data, in which case: Settings → Developer settings → PATs (fine-grained) → repo:read scope → save as `secrets.PROFILE_TOKEN` and swap `GITHUB_TOKEN` → `PROFILE_TOKEN` in `build.yml`.
