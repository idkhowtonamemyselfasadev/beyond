#!/usr/bin/env bash
# Boots the server on the EXISTING run/world (no rebuild, no wipe) and runs throne-check.js.
set -u
RUN="$(cd "$(dirname "$0")" && pwd)"; PORT="${PORT:-25609}"; cd "$RUN" || exit 1
for p in $(pgrep -f "fabric-server-launch.jar nogui"); do
    if [ "$(cat /proc/$p/comm 2>/dev/null)" = "java" ] && [ "$(readlink /proc/$p/cwd)" = "$RUN" ]; then kill "$p"; command sleep 4; fi
done
rm -f console.fifo throne.log; mkfifo console.fifo
java -Xmx2G -jar fabric-server-launch.jar nogui < console.fifo > throne.log 2>&1 &
SERVER_PID=$!; exec 3> console.fifo
cleanup() { echo "stop" >&3 2>/dev/null; wait $SERVER_PID 2>/dev/null; exec 3>&- 2>/dev/null; rm -f console.fifo; }
trap cleanup EXIT
i=0; until grep -qE 'Done \(|Failed to load registries' throne.log || [ $i -ge 240 ]; do command sleep 1; i=$((i+1)); done
grep -qE 'Done \(' throne.log || { echo "!! server did not boot"; tail -20 throne.log; exit 1; }
PORT="$PORT" node throne-check.js 2>&1 | grep -vE "^Chunk size is|^PartialReadError|^\s+at |DeprecationWarning|partial packet"
RESULT=${PIPESTATUS[0]}
echo "--- exceptions:"; grep -iE "exception|ERROR\]" throne.log | grep -v "No key layers" | head -5
echo "--- can't keep up: $(grep -c "Can't keep up" throne.log)"
exit $RESULT
