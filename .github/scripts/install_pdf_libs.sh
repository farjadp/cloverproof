#!/usr/bin/env bash
# System libraries WeasyPrint needs for the proof PDF tests.
#
# Some ubuntu-latest runner images start with no Ubuntu archive in their apt sources (only
# packages.microsoft.com), so these packages cannot be found. Add the official archive, signed
# by the keyring the image ships, only when that happens.
set -euo pipefail

PACKAGES=(libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0)
FALLBACK_LIST="${FALLBACK_LIST:-/etc/apt/sources.list.d/ubuntu-archive-fallback.list}"
KEYRING="${KEYRING:-/usr/share/keyrings/ubuntu-archive-keyring.gpg}"
OS_RELEASE="${OS_RELEASE:-/etc/os-release}"

all_available() {
  local package
  for package in "${PACKAGES[@]}"; do
    apt-cache show --no-all-versions "$package" >/dev/null 2>&1 || return 1
  done
}

sudo apt-get update

if ! all_available; then
  echo "Ubuntu packages missing from the apt sources; adding the Ubuntu archive." >&2
  if [ ! -r "$KEYRING" ]; then
    echo "Cannot add the archive: keyring $KEYRING is missing." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  codename="$(. "$OS_RELEASE" && echo "$VERSION_CODENAME")"
  base="http://archive.ubuntu.com/ubuntu"
  {
    echo "deb [signed-by=$KEYRING] $base $codename main universe"
    echo "deb [signed-by=$KEYRING] $base $codename-updates main universe"
    echo "deb [signed-by=$KEYRING] $base $codename-security main universe"
  } | sudo tee "$FALLBACK_LIST" >/dev/null
  sudo apt-get update
fi

sudo apt-get install -y --no-install-recommends "${PACKAGES[@]}"
