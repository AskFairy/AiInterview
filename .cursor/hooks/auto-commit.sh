#!/bin/bash
set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi

git_dir="$(git rev-parse --git-dir)"
if [[ -f "${git_dir}/MERGE_HEAD" || -d "${git_dir}/rebase-apply" || -d "${git_dir}/rebase-merge" || -f "${git_dir}/CHERRY_PICK_HEAD" ]]; then
  echo '{}'
  exit 0
fi

paths=(
  "聊天记录"
  ".cursor/rules"
  ".cursor/hooks.json"
  ".cursor/hooks/archive-chat.sh"
  ".cursor/hooks/auto-commit.sh"
)

for p in "${paths[@]}"; do
  if [[ -e "${p}" ]]; then
    git add -A -- "${p}" 2>/dev/null || true
  fi
done

if git diff --cached --quiet; then
  echo '{}'
  exit 0
fi

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
mkdir -p ".cursor/hooks/state"
error_log=".cursor/hooks/state/auto-commit-error.log"

if git commit -m "chore: 自动保存聊天记录 ${timestamp}" >/dev/null 2>&1; then
  if git rev-parse '@{u}' >/dev/null 2>&1; then
    if ! git push >/dev/null 2>&1; then
      printf '[%s] auto-push failed (commit 已成功)\n' "${timestamp}" >> "${error_log}"
    fi
  fi
else
  printf '[%s] auto-commit failed\n' "${timestamp}" >> "${error_log}"
fi

echo '{}'
