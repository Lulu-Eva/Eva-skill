#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="eva"
REPO="Lulu-Eva/Eva-skill"
SOURCE_DIR="$HOME/.agents/skills/${SKILL_NAME}"

echo "Installing ${SKILL_NAME}..."

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: npx is required. Please install Node.js first."
  exit 1
fi

npx skills add "${REPO}" -g --all -y

if [ ! -d "${SOURCE_DIR}" ]; then
  echo "Error: ${SOURCE_DIR} was not found after installation."
  exit 1
fi

AGENT_SKILL_DIRS=(
  "$HOME/.workbuddy/skills"
  "$HOME/.cursor/skills"
  "$HOME/.augment/skills"
)

link_skill() {
  local agent_dir="$1"
  local parent_dir
  local target
  parent_dir="$(dirname "${agent_dir}")"
  target="${agent_dir}/${SKILL_NAME}"

  if [ ! -d "${parent_dir}" ]; then
    return 0
  fi

  mkdir -p "${agent_dir}"

  if [ -L "${target}" ]; then
    rm "${target}"
  elif [ -e "${target}" ]; then
    echo "  -> Skipped ${target}: path already exists and is not a symlink."
    return 0
  fi

  ln -s "../../.agents/skills/${SKILL_NAME}" "${target}"
  echo "  -> Linked $(basename "${parent_dir}")"
}

for agent_dir in "${AGENT_SKILL_DIRS[@]}"; do
  link_skill "${agent_dir}"
done

echo ""
echo "Eva-skill installed."
echo "Use /${SKILL_NAME} in supported Agent clients."
echo "If WorkBuddy is already open, restart or refresh it before using /${SKILL_NAME}."
