#!/bin/bash
# Kept for old instructions: builds the Python venvs. Same as: bash setup.sh --python
exec bash "$(cd "$(dirname "$0")/../.." && pwd)/setup.sh" --python
