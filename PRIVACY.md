# Privacy policy

AsBuild, by Hevelius AI Group LLC. Last updated 13 November 2026.

AsBuild collects no personal data. Hevelius AI Group LLC runs no server for AsBuild and receives none of your data: no account, no analytics, no tracking. Hevelius AI Group LLC sees only what GitHub shows any repository's owner: counts of visits to the AsBuild repository and of how often it is copied (cloned), which do not say who made them, and anything you post there yourself, such as an issue.

## Where your data goes

- **The plugin** runs on your computer, inside Claude Code. It sends data only to GitHub, through your own `git` and `gh` and your own GitHub sign-in:
  - setup uploads a branch named `asbuild-setup` with AsBuild's two workflow files, and a `requirements.txt` that lists pytest when yours does not (yours with pytest added, or a new one); on an empty repository it first uploads `main`, holding only a `requirements.txt` (your folder's own, with pytest added when it lacks it, or a new one);
  - the story skill uploads a story branch and opens a story pull request: your request in your own words, the agreed checks and their tests;
  - the AI's builds are uploaded to GitHub on their own branches, as with any pull request;
  - setup opens GitHub's pull request page in your browser, and the verdict wait reads your pull request's checks from GitHub.
- **The two workflow files** run in your own repository's GitHub Actions. They run your tests, then post a check and a comment on your pull request, inside your repository. They use no repository secrets. AsBuild's own steps contact only GitHub and the Python Package Index (PyPI), to install your `requirements.txt` and one package AsBuild uses (`defusedxml`). Your project's own code and tests, which these workflows run, contact whatever they are written to contact.
- **Claude Code, GitHub, PyPI and Anthropic** handle your data under their own policies.

## No warranty, no liability

AsBuild is created by Hevelius AI Group LLC and provided free of charge, "as is", without warranty of any kind. To the fullest extent permitted by law, Hevelius AI Group LLC is not liable for any damage or loss arising from AsBuild or its use; you use it at your own risk and remain responsible for what you merge. The full terms are in [TERMS.md](TERMS.md).

## Questions

Open an issue at https://github.com/hevelius-ai/asbuild/issues.
