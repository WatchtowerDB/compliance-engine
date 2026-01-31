#!/usr/bin/env bash
set -euo pipefail

# ----------------
# ░█░█░█▀█░█▀▄░█▀▀
# ░▀▄▀░█▀█░█▀▄░▀▀█
# ░░▀░░▀░▀░▀░▀░▀▀▀
# ----------------

# NOTE: Colors
__STYLE_RESET='\e[0m'
__STYLE_BOLD='\e[1m'
__STYLE_CYAN='\e[36m'
__STYLE_BCYAN='\e[36;1m'
__STYLE_GREEN='\e[32m'
__STYLE_BGREEN='\e[32;1m'
__STYLE_RED='\e[31m'
__STYLE_BRED='\e[31;1m'
__STYLE_YELLOW='\e[33m'
__STYLE_BYELLOW='\e[33;1m'

__REQUIRED_ENV_VARS=(
  WTCE_BASE_MODEL_PATH
  WTCE_CHROMA_DIR
  WTCE_EMBEDDING_MODEL_DIR
)

# --------------------
# ░█░█░▀█▀░▀█▀░█░░░█▀▀
# ░█░█░░█░░░█░░█░░░▀▀█
# ░▀▀▀░░▀░░▀▀▀░▀▀▀░▀▀▀
# --------------------

# NOTE: Print error message and exit
__errexit() {
  __log error "${1:-Unexpected error}"
  exit 1
}

# NOTE: Logging utility function
__log() {
  local _level="${1:-info}"
  _level="${_level^^}"
  local _msg="${2:-}"

  local _level_color="${__STYLE_BOLD}"
  local _msg_color=""
  case "${_level}" in
  INFO)
    _level_color="${__STYLE_BCYAN}"
    _msg_color="${__STYLE_CYAN}"
    ;;
  SUCCESS)
    _level_color="${__STYLE_BGREEN}"
    _msg_color="${__STYLE_GREEN}"
    ;;
  WARN | WARNING)
    _level_color="${__STYLE_BYELLOW}"
    _msg_color="${__STYLE_YELLOW}"
    ;;
  ERROR)
    _level_color="${__STYLE_BRED}"
    _msg_color="${__STYLE_RED}"
    ;;
  esac

  printf "${_level_color}%s, %s:${__STYLE_RESET}${_msg_color} %s${__STYLE_RESET}\n" "$(date '+%F %H:%M:%S')" "${_level}" "${_msg}" >&2
}

_check_dependencies() {
  for var in "${__REQUIRED_ENV_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
      __errexit "Required environment variable is not defined: ${var}"
    fi
  done

  if [ ! -f "${WTCE_BASE_MODEL_PATH:-}" ]; then
    __errexit "Specified model path is not a regular file: ${WTCE_BASE_MODEL_PATH:-}"
  fi

  if [ ! -d "${WTCE_CHROMA_DIR:-}" ]; then
    __errexit "WTCE_CHROMA_DIR not a valid directory: ${WTCE_CHROMA_DIR:-}"
  fi

  if [ ! -d "${WTCE_EMBEDDING_MODEL_DIR:-}" ]; then
    __errexit "WTCE_EMBEDDING_MODEL_DIR not a valid directory: ${WTCE_EMBEDDING_MODEL_DIR:-}"
  fi
}

_migrate() {
  django-admin migrate
}

_check_superuser() {
  declare _check_output=""
  _check_output="$(
    django-admin shell <<EOF
from django.contrib.auth import get_user_model

User = get_user_model()
username = "admin"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username="admin",
        password="admin"
    )
    print("created")
else:
    print("exists")
EOF
  )"

  if [ "${_check_output}" = "exists" ]; then
    __log info "Superuser found: admin"
  else
    __log info "Superuser created with default credentials"
  fi
}

_serve() {
  wtce server
}

_main() {
  _check_dependencies
  _migrate
  _check_superuser
  _serve
}

_main
