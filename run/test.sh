#!/usr/bin/env bash
# Boots a stock 1.21.11 Fabric server (current stable loader, nothing in mods/ but this jar)
# on a fresh world, then sends one vanilla client through the whole End.
set -u
RUN="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-25609}"
cd "$RUN" || exit 1

if [ "${SKIP_BUILD:-0}" = "1" ]; then
    echo "== using the jar as built (SKIP_BUILD=1) =="
else
    echo "== building =="
    (cd .. && python3 gen/build_data.py && JAVA_HOME=/home/tim/.gradle/jdks/eclipse_adoptium-21-amd64-linux.2 \
        ./gradlew build --offline -q) || exit 1
fi
mkdir -p mods && find mods -name '*.jar' -delete && cp ../build/libs/beyond-1.1.0.jar mods/
sed -i "s/^server-port=.*/server-port=$PORT/" server.properties

# Any server still running out of this directory holds the port.
for p in $(pgrep -f "fabric-server-launch.jar nogui"); do
    if [ "$(cat /proc/$p/comm 2>/dev/null)" = "java" ] && [ "$(readlink /proc/$p/cwd)" = "$RUN" ]; then
        kill "$p"; command sleep 4
    fi
done

rm -f console.fifo test.log bots.log
rm -rf world logs config
mkfifo console.fifo
java -Xmx2G -jar fabric-server-launch.jar nogui < console.fifo > test.log 2>&1 &
SERVER_PID=$!
exec 3> console.fifo
cleanup() { echo "stop" >&3 2>/dev/null; wait $SERVER_PID 2>/dev/null; exec 3>&- 2>/dev/null; rm -f console.fifo; }
trap cleanup EXIT

waitfor() {
    local pattern="$1" limit="${2:-120}" i=0
    while [ $i -lt "$limit" ]; do grep -qE "$pattern" test.log && return 0; command sleep 1; i=$((i + 1)); done
    echo "!! TIMED OUT waiting for: $pattern"; return 1
}

echo "== booting on port $PORT =="
# A registry error kills the boot long before the 240 s are up, so stop on either.
waitfor 'Done \(|Failed to load registries' 240 || { tail -30 test.log; exit 1; }
if grep -qE 'Failed to load registries|Failed to parse beyond:worldgen/biome' test.log; then
    echo "!! FAIL  the server loaded its registries  (test.log has a registry error)"
    grep -m3 -oE 'Failed to (get element|parse) [^ ]+( [^ ]+)?' test.log | sort -u
    exit 1
fi
grep -E "Loading Minecraft|^\s+- beyond|Beyond the End ready|Registered /beyond" test.log
# Logging on, so assertions can also read what fired.
mkdir -p config
python3 - <<'PY'
import json
p='config/beyond.json'
try: d=json.load(open(p))
except Exception: d={}
d['log_events']=True; d['structure_spacing_chunks']=6; d['portal_spacing_chunks']=10
d['pack_url']=''   # the run is about the mod, not the download; section 10 checks nothing is pushed
json.dump(d, open(p,'w'), indent=2)
PY
echo "beyond reload" >&3
command sleep 2

PORT="$PORT" node test-bots.js 2>&1 \
  | grep -vE "^Chunk size is|^PartialReadError|^\s+at |DeprecationWarning|trace-deprecation|partial packet" \
  | tee bots.log
RESULT=${PIPESTATUS[0]}

echo
echo "=========== SERVER-SIDE ==========="
grep -oE "(EVENT .*|Structure placed: .*)" test.log | head -30
echo
echo "=========== EXCEPTIONS ==========="
grep -iE "exception|ERROR\]" test.log | grep -v "No key layers" | head -15 || true
echo
echo "=========== SERVER-SIDE CHECKS ==========="
SFAIL=0
spass() { echo "   PASS  $1${2:+  $2}"; }
sfail() { echo "!! FAIL  $1${2:+  $2}"; SFAIL=$((SFAIL + 1)); }
if grep -qE 'Failed to load registries|Failed to parse beyond:worldgen/biome' test.log; then
    sfail "the server loaded its registries"; else spass "the server loaded its registries"; fi
BAD=$(grep -E 'Exception|ERROR\]' test.log | grep -v "No key layers" | grep -iE 'beyond|Rivers|BossLocator|PackOffer|castles' | head -3)
if [ -n "$BAD" ]; then sfail "no exception or ERROR mentions the mod" "$BAD"; else spass "no exception or ERROR mentions the mod"; fi
SND=$(grep -iE 'Failed to load sound|Unknown sound|Missing sound|sound event' test.log | grep -viE 'INFO\]' | head -3)
if [ -n "$SND" ]; then sfail "no sound errors" "$SND"; else spass "no sound errors"; fi
# Rivers are carved around players by chance, so this is a report, not an assertion.
RIVERS=$(grep -c 'River carved' test.log)
echo "   rivers carved: $RIVERS  sizes: $(grep -oE 'River carved: [0-9]+' test.log | grep -oE '[0-9]+$' | tr '\n' ' ')"
grep -E 'River carved' test.log | head -5
CASTLES=$(grep -c 'Castle placed' test.log)
echo "   castles placed: $CASTLES  $(grep -oE 'Castle placed: [a-z_]+' test.log | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
grep -E 'Castle placed' test.log | head -5
GARRISONS=$(grep -c 'Castle garrison' test.log)
echo "   castles garrisoned: $GARRISONS  $(grep -oE 'Castle garrison: [0-9]+ of [0-9]+ for [a-z_]+' test.log | tr '\n' ';')"
if [ "$CASTLES" -gt 0 ] && [ "$GARRISONS" -ne "$CASTLES" ]; then echo "!! FAIL  every placed castle should log a garrison ($GARRISONS of $CASTLES)"; SFAIL=$((SFAIL + 1)); fi
HALLS=$(grep -c 'Boss hall placed' test.log)
echo "   boss halls placed: $HALLS  $(grep -oE 'Boss hall placed: [a-z_]+' test.log | sort | uniq -c | tr -s ' ' | tr '\n' ';')"
if [ "$HALLS" -lt 2 ]; then sfail "both boss halls were built during the run" "$HALLS"; else spass "both boss halls were built during the run" "$HALLS"; fi
for w in "void warden woken" "void warden killed" "gale sovereign woken" "gale sovereign killed"; do
    if grep -q "EVENT $w" test.log; then spass "the log shows: $w"; else sfail "the log shows: $w"; fi
done
if grep -q 'ConcurrentModificationException' test.log; then sfail "no ConcurrentModificationException"; else spass "no ConcurrentModificationException"; fi
echo "   'Can't keep up' warnings: $(grep -c "Can't keep up" test.log)"
echo "(end)"
[ "$RESULT" -eq 0 ] && [ "$SFAIL" -eq 0 ] && exit 0
exit 1
