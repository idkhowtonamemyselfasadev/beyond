#!/usr/bin/env bash
# Boots the test server the way test.sh does (fresh world, only this jar in mods/) and
# asks it, over the console, whether the three castles exist: `locate` proves the
# structure set and biome tag, `place structure` proves the jigsaw structure JSON, and
# `place template` plus a block check at a known chest proves the NBT itself loads.
# Kills only a server whose cwd is this directory; never anything else on the machine.
set -u
RUN="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-25609}"
cd "$RUN" || exit 1

mkdir -p mods && find mods -name '*.jar' -delete && cp ../build/libs/beyond-1.1.0.jar mods/
sed -i "s/^server-port=.*/server-port=$PORT/" server.properties
for p in $(pgrep -f "fabric-server-launch.jar nogui"); do
    if [ "$(cat /proc/$p/comm 2>/dev/null)" = "java" ] && [ "$(readlink /proc/$p/cwd)" = "$RUN" ]; then
        kill "$p"; command sleep 4
    fi
done

rm -f console.fifo test.log
rm -rf world logs config
mkfifo console.fifo
java -Xmx3G -jar fabric-server-launch.jar nogui < console.fifo > test.log 2>&1 &
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
waitfor 'Done \(' 300 || { tail -30 test.log; exit 1; }
grep -E "Beyond the End ready|Installed data pack" test.log

FAIL=0
for s in obsidian_fortress purpur_citadel tide_bastion; do
    echo "execute in minecraft:the_end run locate structure beyond:$s" >&3
    waitfor "nearest beyond:$s|Could not find.*$s" 120 || FAIL=1
done

# Nobody is in the End, so its chunks have to be force-loaded before anything can be
# placed there. A jigsaw start piece gets a random rotation, so a castle can extend up to
# its full width in the negative direction from its origin: load a wide square round each
# point, in quarters, because one forceload command takes at most 256 chunks.
load() {   # centre x, centre z, half-width
    local x="$1" z="$2" h="$3"
    for q in "-$h -$h -1 -1" "0 -$h $h -1" "-$h 0 -1 $h" "0 0 $h $h"; do
        set -- $q
        echo "execute in minecraft:the_end run forceload add $((x + $1)) $((z + $2)) $((x + $3)) $((z + $4))" >&3
    done
}
load 600 100 130; load 900 100 130; load 1200 100 130
load 140 140 60; load 344 140 60; load 140 344 60
echo "waiting for the End to generate those chunks"; command sleep 60

# One jigsaw placement of each. A forceloaded chunk is not loaded until the End has
# generated it, so a placement that lands too early is tried again after a wait.
since() { wc -l < test.log; }
waitsince() {   # pattern, offset, limit: like waitfor, but only in lines after the offset
    local pattern="$1" off="$2" limit="${3:-120}" i=0
    while [ $i -lt "$limit" ]; do
        tail -n +$((off + 1)) test.log | grep -qE "$pattern" && return 0
        command sleep 1; i=$((i + 1))
    done
    echo "!! TIMED OUT waiting for: $pattern"; return 1
}
place() {   # kind, name, x, y, z
    local kind="$1" name="$2" x="$3" y="$4" z="$5" tries=0 off
    while [ $tries -lt 12 ]; do
        off=$(since)
        echo "execute in minecraft:the_end run place $kind $name $x $y $z" >&3
        waitsince "Generated structure|Loaded template|Failed|Unknown|does not exist|not loaded" "$off" 300 || return 1
        if tail -n +$((off + 1)) test.log | grep -q "not loaded"; then
            echo "  $name at $x $z: chunks not loaded yet, waiting"; command sleep 30; tries=$((tries + 1))
        else
            tail -n +$((off + 1)) test.log | grep -E "Generated structure|Loaded template|Failed|Unknown|does not exist" \
                | sed -E 's/^\[[^]]*\] \[[^]]*\]: /  /'
            tail -n +$((off + 1)) test.log | grep -qE "Generated structure|Loaded template"; return $?
        fi
    done
    echo "!! $name never had its chunks loaded"; return 1
}
place structure beyond:obsidian_fortress 600 60 100 || FAIL=1
place structure beyond:purpur_citadel 900 60 100 || FAIL=1
place structure beyond:tide_bastion 1200 60 100 || FAIL=1

# The raw templates at exact positions, and a chest each where the generator put one.
place template beyond:obsidian_fortress/0 96 40 96 || FAIL=1
echo "execute in minecraft:the_end run data get block 108 52 104 LootTable" >&3
waitfor "108, 52, 104 has the following block data|has no block data|is not a block entity" 60 || FAIL=1
place template beyond:purpur_citadel/0 300 40 96 || FAIL=1
echo "execute in minecraft:the_end run data get block 340 64 130 LootTable" >&3
waitfor "340, 64, 130 has the following block data|has no block data|is not a block entity" 60 || FAIL=1
place template beyond:tide_bastion/0 96 40 300 || FAIL=1
echo "execute in minecraft:the_end run data get block 101 52 301 LootTable" >&3
waitfor "101, 52, 301 has the following block data|has no block data|is not a block entity" 60 || FAIL=1
command sleep 2

echo
echo "=========== RESULTS ==========="
grep -E "nearest beyond:|Could not find|Generated structure|Loaded template|Failed|not loaded|has the following block data|has no block data|is not a block entity|Unknown|does not exist" test.log \
    | sed -E 's/^\[[^]]*\] \[[^]]*\]: //'
echo
echo "=========== ERRORS ==========="
grep -iE "exception|ERROR\]|Failed to load|Unable|Missing|Couldn't" test.log | grep -v "No key layers" | head -20 || true
echo "(end)"
exit $FAIL
