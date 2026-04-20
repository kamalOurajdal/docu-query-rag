#!/bin/bash
# -----------------------------------------------------------------------------
# Usage: ./run.sh <folder_name> [--port N]
# This script detects if the folder is Flask or Angular and runs it.
# -----------------------------------------------------------------------------

# ------------------ PORT MAP (DEFAULT PORTS) ------------------
# declare -A means: "associative array" (a map: key -> value)
# Example: PORTS["ep-api"]=5000

declare -A PORTS=(
  # Flask services (backend)
  [esg-api]=5000
  [esg-report]=5002
  [esg-collect]=5004
  [esg-notification]=5005
  [esg-carbon]=5001
  [esg-user]=5003
  [esg-mail]=5007
  [esg-externe]=5006
  [esg-ui]=4200
  [esg-ui-external]=4201
  [docu-query]=5008
)

# Default port if the folder is Flask but not in the map
DEFAULT_FLASK_PORT=5000

# Default port if the folder is Angular but not in the map
DEFAULT_ANGULAR_PORT=4200
# --------------------------------------------------------------

# Get the absolute path of the directory where this script exists
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read the first argument as folder name; if missing, show usage and stop
FOLDER="${1:?Usage: run.sh <folder> [--port N]}"
# remove / in the beginning and end of the folder
FOLDER="${FOLDER%/}"
FOLDER="${FOLDER#/}"

# Remove the first argument, so we can read the flags (like --port)
shift

# Set terminal title to the folder name (nice for multiple terminal tabs)
# \033]0;  starts title change, \007 ends it
echo -ne "\033]0;${FOLDER}\007"

# This will store the optional port passed by user like: --port 5050
PORT_ARG=""

# Read remaining args to find --port
while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      PORT_ARG="$2"   # take the number after --port
      shift 2         # skip both "--port" and the number
      ;;
    *)
      shift           # ignore any other argument
      ;;
  esac
done

# Build the full path to the folder the user asked to run
DIR="$SCRIPT_DIR/$FOLDER"

# If folder doesn’t exist, stop
if [ ! -d "$DIR" ]; then
  echo "[ERROR] Folder not found: $FOLDER"
  exit 1
fi

# ------------------ HELPER FUNCTION ------------------
# This function returns:
# - the port from the map if the folder exists in PORTS
# - otherwise it returns a fallback port
get_default_port() {
  local folder="$1"     # first param: folder name
  local fallback="$2"   # second param: fallback port if not found

  # If PORTS[folder] is not empty, return it
  if [[ -n "${PORTS[$folder]}" ]]; then
    echo "${PORTS[$folder]}"
  else
    # Otherwise return fallback
    echo "$fallback"
  fi
}
# -----------------------------------------------------

# -----------------------------------------------------------------------------
# FLASK (PYTHON) DETECTION
# If application.py exists, we treat it as a Flask service
# -----------------------------------------------------------------------------
if [ -f "$DIR/application.py" ]; then
  # Tell Flask which file is the entry point
  export FLASK_APP="application.py"

  # Activate venv (Windows Git Bash path)
  if [ -f "$DIR/.venv/Scripts/activate" ]; then
    source "$DIR/.venv/Scripts/activate"

  # Activate venv (Linux/Mac path)
  elif [ -f "$DIR/.venv/bin/activate" ]; then
    source "$DIR/.venv/bin/activate"

  # check for venv
  elif [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
  elif [ -f "$DIR/venv/Scripts/activate" ]; then
    source "$DIR/venv/Scripts/activate"

  else
    # If no venv found, show error and stop
    echo "[ERROR] $FOLDER: .venv not found. Create it with: cd $FOLDER && python -m venv .venv"
    exit 1
  fi

  # Find the default port: from map or fallback Flask port
  DEFAULT_PORT="$(get_default_port "$FOLDER" "$DEFAULT_FLASK_PORT")"

  # Choose final port:
  # if user passed --port use it, otherwise use DEFAULT_PORT
  PORT="${PORT_ARG:-$DEFAULT_PORT}"

  # Print what we are going to do
  echo "Starting $FOLDER (Flask) on port $PORT..."

  # Move inside the service folder
  cd "$DIR" || exit 1

  # Run Flask on that port
  echo "python3.8 application.py run"
  python3.8 "$DIR/application.py" run

  # Stop script after running the service
  exit 0
fi

# -----------------------------------------------------------------------------
# ANGULAR DETECTION
# If package.json and angular.json exist, we treat it as Angular app
# -----------------------------------------------------------------------------
if [ -f "$DIR/package.json" ] && [ -f "$DIR/angular.json" ]; then

  # Find the default port: from map or fallback Angular port
  DEFAULT_PORT="$(get_default_port "$FOLDER" "$DEFAULT_ANGULAR_PORT")"

  # Choose final port:
  # if user passed --port use it, otherwise use DEFAULT_PORT
  PORT="${PORT_ARG:-$DEFAULT_PORT}"

  # Print what we are going to do
  echo "Starting $FOLDER (Angular) on port $PORT..."

  # Move inside the app folder
  cd "$DIR" || exit 1

  # Run Angular dev server on that port
  npx ng serve --port "$PORT"

  # Stop script after running the app
  exit 0
fi

# If it is neither Flask nor Angular, we don’t know how to run it
echo "[ERROR] $FOLDER: Not detected as Flask (application.py) or Angular (package.json + angular.json)."
exit 1
