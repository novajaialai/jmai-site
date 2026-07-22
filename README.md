# jmai-site

Source for **jacobdart.com** (Jacob Dart, J&M AI Services). Static site served via GitHub Pages.
Canonical full source lives in the private `novajaialai/jacobdart` repo.

## Canonical (2026-07-21)

This repo IS the site — canonical source and deploy target in one. GitHub Pages
serves `main` at jacobdart.com; push = deploy. The former two-repo setup
(`~/projects/jacobdart` canonical → rsync mirror → here) was retired 2026-07-21
after the mirror clobbered the live homepage; archive at
`~/archive/jacobdart-retired-2026-07-21`.

Blog: write `content/posts/*.md`, run `python3 tools/build_blog.py`, commit.
