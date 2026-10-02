#!/usr/bin/env bash
# Crea una copia usa-e-getta della wiki di esempio, in un repo git locale,
# e stampa il comando per aprirla con il plugin di questo repo.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WIKI="$(mktemp -d)/sample-wiki"
cp -R "$REPO/tests/fixtures/sample-wiki" "$WIKI"
cd "$WIKI"
git init -q -b main
git add -A
git commit -q -m "fixture"
echo "WIKI=$WIKI"
echo "REPO=$REPO"
echo "Apri con:  cd \"$WIKI\" && claude --plugin-dir \"$REPO\""
