#!/bin/bash

# ------------------------------------------------------------------
# Runs every suite in this repo on Sauce Labs (eu-central-1), tagged so the jobs are easy
# to find in the Sauce Labs UI (repo:demo-python, framework:*, cli:*, usecase:*, ...).
# Used by hand and by the daily 10:00 launchd job (~/scripts/run_sauce_tests.sh).
#
# Self-contained: loads its own credentials, PATH and per-suite virtualenvs, writes only to
# its own log, and does not rely on anything the calling job sets up.
#
# Credentials: SAUCE_USERNAME / SAUCE_ACCESS_KEY from the environment, else read from the
# `export NAME=value` lines in ~/.zshrc (cron/launchd do not load the shell profile).
# Extra tags: SAUCE_TAGS (default "ci:cron") is appended to every job's tags; set
# SAUCE_TAGS="" for a manual run.
# ------------------------------------------------------------------

# Project root (this script lives in <repo>/scripts; resolve symlinks so it can be called via ~/scripts)
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"

zshrc_var() {
    sed -n "s/^export $1=//p" "$HOME/.zshrc" 2>/dev/null | tail -1 | tr -d "\"'"
}
for var in SAUCE_USERNAME SAUCE_ACCESS_KEY; do
    [ -z "${!var}" ] && export "$var=$(zshrc_var "$var")"
done
export SAUCE_REGION=eu-central-1
export SAUCE_TAGS="${SAUCE_TAGS-ci:cron}"

export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
PYTHON="$(command -v python3.13 || command -v python3)"

# One virtualenv per suite, inside the suite's own directory (gitignored)
export PIPENV_VENV_IN_PROJECT=1
# Ignore any virtualenv the caller has activated, or pipenv installs every suite into it
export PIPENV_IGNORE_VIRTUALENVS=1
unset VIRTUAL_ENV
export PIPENV_VERBOSITY=-1
export PIPENV_YES=1

# Own log only - never inherit another repo's LOG_FILE
LOG_FILE="${PYTHON_LOG_FILE:-$HOME/sauce_automation_python.log}"
BUILD_DATE="$(date +%Y-%m-%d)"

# Keep the Mac awake for the whole run.
caffeinate -i -w $$ &

echo "--------------------------------------------------" >> "$LOG_FILE"
echo "Starting Sauce Labs Python Tests: $(date)" >> "$LOG_FILE"
echo "Branch: $(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD) @ $(git -C "$PROJECT_DIR" rev-parse --short HEAD)" >> "$LOG_FILE"

for var in SAUCE_USERNAME SAUCE_ACCESS_KEY; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set (export it in ~/.zshrc)." >> "$LOG_FILE"
        exit 1
    fi
done

FAILED=0

# $1 = suite dir (relative to repo root), $2.. = command run through `pipenv run`
run_suite() {
    local dir="$1"
    shift
    pushd "$PROJECT_DIR/$dir" > /dev/null || { echo "FAILURE: missing $dir" >> "$LOG_FILE"; FAILED=1; return; }
        # Keeps each suite's virtualenv in sync with its Pipfile.lock (no-op when up to date)
        "$PYTHON" -m pipenv sync --python "$PYTHON" >> "$LOG_FILE" 2>&1
        echo "Running ($dir, tags=+$SAUCE_TAGS): $*" >> "$LOG_FILE"
        if "$PYTHON" -m pipenv run "$@" >> "$LOG_FILE" 2>&1; then
            echo "SUCCESS: $dir: $*" >> "$LOG_FILE"
        else
            echo "FAILURE: $dir: $*" >> "$LOG_FILE"
            FAILED=1
        fi
    popd > /dev/null
}

# --- 1. Best practice: desktop web (Selenium + pytest, 5 browsers) ---
echo "--- Section: Best Practice Desktop Web ---" >> "$LOG_FILE"
BUILD_TAG="demo-python desktop-web $BUILD_DATE" \
    run_suite best_practice/desktop_web best-practice-desktop-eu

# --- 2. Best practice: mobile web (emulators/simulators, then real iOS devices) ---
echo "--- Section: Best Practice Mobile Web ---" >> "$LOG_FILE"
BUILD_TAG="demo-python mobile-web-vdc $BUILD_DATE" \
    run_suite best_practice/mobile_web best-practice-mobile-web-vdc-eu
run_suite best_practice/mobile_web best-practice-mobile-web-rdc-eu

# --- 3. Best practice: native apps on real devices (Appium + pytest) ---
echo "--- Section: Best Practice Mobile Native ---" >> "$LOG_FILE"
run_suite best_practice/mobile_native best-practice-mobile-native-eu-android
run_suite best_practice/mobile_native best-practice-mobile-native-eu-ios

# --- 4. Playwright (pytest-playwright, Sauce Labs Playwright sessions) ---
echo "--- Section: Playwright ---" >> "$LOG_FILE"
TARGET=sauce SAUCE_BUILD_NAME="demo-python playwright $BUILD_DATE" \
    run_suite examples/playwright playwright-tests

# --- 5. Selenium 4 feature examples ---
echo "--- Section: Selenium Examples ---" >> "$LOG_FILE"
BUILD_TAG="demo-python selenium4-features $BUILD_DATE" \
    run_suite examples/selenium demo

# --- 6. Robot Framework: desktop web (SeleniumLibrary) and native apps (AppiumLibrary) ---
echo "--- Section: Robot Framework ---" >> "$LOG_FILE"
run_suite examples/robotframework/desktop_web robot-desktop-web-eu
run_suite examples/robotframework/native_mobile robot-android-eu
run_suite examples/robotframework/native_mobile robot-ios-eu

echo "All Python tests completed: $(date)" >> "$LOG_FILE"
echo "--------------------------------------------------" >> "$LOG_FILE"
exit $FAILED
