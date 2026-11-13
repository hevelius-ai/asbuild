# Privacy policy

AsBuild, by Hevelius AI Group LLC. Last updated 13 November 2026.

AsBuild collects no personal data. Hevelius AI Group LLC runs no server for AsBuild and receives nothing from it: no account, no analytics, no tracking.

## What AsBuild does with your data

- **The plugin** runs on your computer, inside Claude Code. Its scripts use your own `git` and `gh`, with your own GitHub sign-in, to read your repository and to upload one branch named `asbuild-setup` that holds AsBuild's two workflow files (and, on an empty repository, a first `requirements.txt`). Nothing else leaves your computer, and nothing goes to Hevelius AI Group LLC.
- **The two workflow files** run in your own repository's GitHub Actions. They run your tests, then post a check and a comment on your pull request, inside your repository. They use no repository secrets, and they send nothing outside GitHub.
- **Claude Code, GitHub and Anthropic** handle your data under their own policies.

## Questions

Open an issue at https://github.com/hevelius-ai/asbuild/issues.
