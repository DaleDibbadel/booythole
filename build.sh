#!/usr/bin/env bash
# Bootyhole registry build. Replaces the template's build_all_branches.sh, which force-checked-out every branch,
# edited next.config.js with sed and swallowed errors. This script builds only the checked-out tree, never touches git state,
# and stops on the first failure. Output: ./public/ (root index + 1.1/ catalog and site). Run from the repository root.
set -euo pipefail
SCHEMA="1.1"                              # Kasm registry schema version; must match basePath in site/next.config.js
grep -q "basePath: '/booythole/${SCHEMA}'" site/next.config.js || { echo "basePath in site/next.config.js is not /booythole/${SCHEMA}" >&2; exit 1; }
node processing/imageref.test.js            # image-reference validator self-test (accepts owner images, refuses malformed ones)
rm -rf public base process
node processing                           # writes ./public/list.json, versions.json, icons/ (async; verified below)
test -s public/list.json || { echo "processing produced no list.json" >&2; exit 1; }
cp -a public/. process
npm run deploy --prefix site              # next build + export into ./public (wipes it)
test -s public/index.html || { echo "site build produced no index.html" >&2; exit 1; }
cp -a process/. public/                   # put the catalog back
rm -rf process
mkdir base
mv public "base/${SCHEMA}"
cp "base/${SCHEMA}/favicon.ico" base/favicon.ico
printf '<meta http-equiv="refresh" content="0; url=./%s/">\n' "${SCHEMA}" > base/index.html
echo "${SCHEMA}" > base/versions.txt
touch base/.nojekyll
mv base public
node processing/verify.js public "${SCHEMA}"
