#!/usr/bin/env bash
set -euo pipefail

# MedFabric environment bootstrap:
# 1) initialize database
# 2) download dataset from DATASET_URL in .env
# 3) if archive, extract into data_sets/
# 4) run importer.py in extracted folder

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"
DATASETS_DIR="$ROOT_DIR/data_sets"
DOWNLOAD_DIR="$DATASETS_DIR/downloads"

mkdir -p "$DATASETS_DIR" "$DOWNLOAD_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env not found at $ENV_FILE"
  exit 1
fi

get_env_value() {
  local key="$1"
  awk -F= -v k="$key" '$1 == k {print substr($0, index($0,$2)); exit}' "$ENV_FILE" | tr -d '\r'
}

DATASET_URL="$(get_env_value DATASET_URL || true)"

if [ -z "$DATASET_URL" ]; then
  echo "Error: DATASET_URL is missing in .env"
  echo "Add: DATASET_URL=https://example.com/dataset.zip"
  exit 1
fi

PYTHON_BIN=""
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Error: Python not found"
  exit 1
fi

echo "[1/4] Initializing database..."
"$PYTHON_BIN" -m medfabric.db.utils.init_db

filename_from_url() {
  local url="$1"
  local base
  base="$(basename "${url%%\?*}")"
  if [ -z "$base" ] || [ "$base" = "/" ] || [ "$base" = "." ]; then
    base="dataset_download"
  fi
  printf "%s" "$base"
}

ARCHIVE_NAME="$(filename_from_url "$DATASET_URL")"
ARCHIVE_PATH="$DOWNLOAD_DIR/$ARCHIVE_NAME"

echo "[2/4] Downloading dataset from DATASET_URL..."
if command -v curl >/dev/null 2>&1; then
  curl -L "$DATASET_URL" -o "$ARCHIVE_PATH"
elif command -v wget >/dev/null 2>&1; then
  wget "$DATASET_URL" -O "$ARCHIVE_PATH"
else
  echo "Error: neither curl nor wget is available"
  exit 1
fi

EXTRACT_ROOT="$DATASETS_DIR"
EXTRACTED_DIR=""

extract_archive() {
  local archive="$1"
  local lower
  lower="$(printf '%s' "$archive" | tr '[:upper:]' '[:lower:]')"

  if [[ "$lower" == *.zip ]]; then
    unzip -o "$archive" -d "$EXTRACT_ROOT" >/dev/null
    return 0
  fi

  if [[ "$lower" == *.tar.gz ]] || [[ "$lower" == *.tgz ]]; then
    tar -xzf "$archive" -C "$EXTRACT_ROOT"
    return 0
  fi

  if [[ "$lower" == *.tar.bz2 ]] || [[ "$lower" == *.tbz2 ]]; then
    tar -xjf "$archive" -C "$EXTRACT_ROOT"
    return 0
  fi

  if [[ "$lower" == *.tar.xz ]] || [[ "$lower" == *.txz ]]; then
    tar -xJf "$archive" -C "$EXTRACT_ROOT"
    return 0
  fi

  if [[ "$lower" == *.tar ]]; then
    tar -xf "$archive" -C "$EXTRACT_ROOT"
    return 0
  fi

  return 1
}

echo "[3/4] Handling dataset payload..."
if extract_archive "$ARCHIVE_PATH"; then
  echo "Archive extracted to $EXTRACT_ROOT"

  IMPORTER_PATH="$(find "$EXTRACT_ROOT" -type f -name importer.py -print | head -n 1 || true)"
  if [ -z "$IMPORTER_PATH" ]; then
    echo "Error: importer.py not found after extraction under $EXTRACT_ROOT"
    exit 1
  fi

  EXTRACTED_DIR="$(dirname "$IMPORTER_PATH")"
else
  echo "Downloaded file is not a supported archive."
  echo "Skipping extraction and importer run."
  echo "File kept at: $ARCHIVE_PATH"
  exit 0
fi

echo "[4/4] Running dataset importer..."
(
  cd "$EXTRACTED_DIR"
  "$PYTHON_BIN" importer.py
)

echo "Done. Environment initialized successfully."
