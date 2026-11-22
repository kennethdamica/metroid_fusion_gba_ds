# Put the project on GitHub

These steps publish the source repository. The local folder is not yet a Git
repository. Run the commands from its root; do not upload the whole folder
through a browser or force-add ignored files.

## 1. Create an empty repository

On GitHub, select **New repository** and choose a name such as `fusion-ds`.
Select **Public** if that is your intended visibility. Leave the options to add
a README, `.gitignore` and license unchecked: local documentation and ignore
rules are already prepared, and no blanket project license has been selected.

Copy the HTTPS repository URL from GitHub's setup page.

## 2. Initialize, check and commit locally

```sh
git init -b main
git add .
python3 tools/check_repository.py
python3 -m unittest discover -s tests/public -v
git diff --cached --stat
git diff --cached --name-only
```

Review the staged list. It should contain source, documentation, patches,
license notices and GitHub configuration. ROMs, BIOS files, generated NDS files,
saves, `vendor/`, `.tools/`, `.venv/` and `artifacts/` should not be staged.
The checker also detects private files already tracked despite ignore rules.
Stop and correct any checker failures before committing.

Then commit:

```sh
git commit -m "Initial Fusion DS source import"
```

If Git asks for your identity, configure it for this repository and retry:

```sh
git config user.name "Your Name"
git config user.email "YOUR_GITHUB_COMMIT_EMAIL"
```

You can use the exact GitHub-provided no-reply address shown in your account's
email settings instead of a personal address.

## 3. Authenticate and push

If GitHub CLI is installed, `gh auth login` provides a browser-based sign-in.
Otherwise use your configured Git credential manager or SSH setup. GitHub
account passwords are not used for HTTPS Git authentication; see
[GitHub authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

Replace `YOUR_USERNAME` and the repository name below with your actual URL:

```sh
git remote add origin https://github.com/YOUR_USERNAME/fusion-ds.git
git remote -v
git push -u origin main
```

For an existing local repository/remote, inspect `git status` and
`git remote -v` first rather than redoing initialization or adding `origin`.
Do not use a force push for this initial upload.

## 4. Check the GitHub page

Confirm the README renders and the **Actions → Source checks** jobs run on
Ubuntu and Windows. Those jobs verify source and public CLI tests; they do not
establish gameplay, hardware or frozen-executable compatibility.

Suggested description: “Dual-screen Metroid Fusion for DS-family hardware,
with a live map and a local ROM-to-NDS packager.” Add a download link to the
README only after a release asset exists.

## Optional: share packager previews separately

Use GitHub **Releases** for standalone executable ZIPs, rather than committing
binaries to the source tree. Refreshed local preview ZIPs and checksums are in
`artifacts/packager-with-notices/`. They contain the same previously tested
executables, with additional notices and a packaging record. The original
build manifests remain intact and describe the executable build.

If you choose to publish them, mark the release as a **pre-release** and state
the current unsigned/native-Windows testing limits. Upload only the two named
platform ZIPs and `SHA256SUMS`, never the whole `artifacts/` directory or a
generated `Fusion.nds`. Keep the documented licensing status factual; the
notice update is not a determination that unknown permissions are resolved.

The upstream-permission questions are deferred by the maintainer; no request
has been sent. Known notices and scoped GPL patch attribution are retained.
See [licensing status](../LICENSING.md) for the precise scope.

These steps follow [GitHub's existing-project import guide](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).
