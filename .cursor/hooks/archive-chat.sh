#!/bin/bash
set -euo pipefail

event_type="${1:-unknown}"
project_root="$(pwd)"
log_dir="${project_root}/聊天记录"
raw_dir="${log_dir}/raw"
brief_dir="${log_dir}/简版"
state_dir="${project_root}/.cursor/hooks/state"

mkdir -p "${raw_dir}" "${brief_dir}" "${state_dir}"

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
payload="$(cat)"

if ! command -v python3 >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi

session_id="$(printf '%s' "${payload}" | python3 -c '
import json, re, sys
raw = sys.stdin.read()
try:
    obj = json.loads(raw)
except Exception:
    print("unknown-session")
    raise SystemExit(0)

targets = {"sessionid", "session_id", "conversationid", "conversation_id", "chatid", "chat_id"}

def walk(v):
    if isinstance(v, dict):
        for k, val in v.items():
            lk = str(k).lower()
            if lk in targets and isinstance(val, (str, int)):
                return str(val)
            found = walk(val)
            if found:
                return found
    elif isinstance(v, list):
        for item in v:
            found = walk(item)
            if found:
                return found
    return None

sid = walk(obj) or "unknown-session"
sid = re.sub(r"[^A-Za-z0-9._-]+", "_", sid)[:120] or "unknown-session"
print(sid)
')"

raw_file="${raw_dir}/会话-${session_id}.jsonl"
brief_file="${brief_dir}/会话-${session_id}.md"
state_user_file="${state_dir}/last-user-${session_id}.txt"

printf '%s\n' "${payload}" >> "${raw_file}"

extract_text() {
  printf '%s' "${payload}" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    obj = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

preferred = [
    "final_response", "finalResponse", "response", "assistant_response", "assistantResponse",
    "prompt", "user_prompt", "userPrompt", "message", "content", "text"
]

def flatten(v):
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, (int, float, bool)):
        return [str(v)]
    if isinstance(v, dict):
        out = []
        for key in preferred:
            if key in v:
                out.extend(flatten(v[key]))
        for key, val in v.items():
            if key not in preferred:
                out.extend(flatten(val))
        return out
    if isinstance(v, list):
        out = []
        for item in v:
            out.extend(flatten(item))
        return out
    return []

texts = flatten(obj)
print(texts[0] if texts else "")
'
}

if [[ "${event_type}" == "user_prompt" ]]; then
  user_text="$(extract_text)"
  printf '%s\n' "${user_text}" > "${state_user_file}"
  {
    printf '## %s\n\n' "${timestamp}"
    printf '**用户提问**\n%s\n\n' "${user_text:-（未捕获到用户提问）}"
    printf '**状态**\n等待AI回复\n\n'
    printf '%s\n\n' '---'
  } >> "${brief_file}"
elif [[ "${event_type}" == "response" ]]; then
  ai_text="$(extract_text)"
  if [[ -f "${state_user_file}" ]]; then
    user_text="$(<"${state_user_file}")"
  else
    user_text=""
  fi
  {
    printf '## %s\n\n' "${timestamp}"
    printf '**用户提问**\n%s\n\n' "${user_text:-（未捕获到用户提问）}"
    printf '**AI最终回复**\n%s\n\n' "${ai_text:-（未捕获到AI回复）}"
    printf '%s\n\n' '---'
  } >> "${brief_file}"
elif [[ "${event_type}" == "session_end" ]]; then
  : # full JSON already appended to raw file
fi

echo '{}'
