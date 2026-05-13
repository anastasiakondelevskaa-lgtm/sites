#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ -z "${GH_TOKEN:-}" ]; then
  echo "session-start: GH_TOKEN not set; skipping git credential setup" >&2
  exit 0
fi

REMOTE_URL="$(git config --get remote.origin.url || true)"
case "$REMOTE_URL" in
  *github.com*) ;;
  *)
    OWNER_REPO="$(printf '%s' "$REMOTE_URL" | sed -E 's#.*/git/([^/]+/[^/]+)$#\1#')"
    if [ -n "$OWNER_REPO" ] && [ "$OWNER_REPO" != "$REMOTE_URL" ]; then
      git remote set-url origin "https://github.com/${OWNER_REPO}.git"
    fi
    ;;
esac

git config --global credential.helper store
umask 077
printf 'https://x-access-token:%s@github.com\n' "$GH_TOKEN" > "$HOME/.git-credentials"

echo "session-start: git credentials configured for github.com" >&2
