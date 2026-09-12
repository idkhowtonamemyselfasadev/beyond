#!/usr/bin/env bash
# In-game screenshots of the End: boots a private Beyond server on port 25607 with the
# current jar, then drives the hidden dev client (weston headless) through script.txt.
#   ./shots.sh                     # SCRIPT=other.txt to run another script
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
MOD="$(dirname "$DIR")"
SRV="$DIR/server"
GRADLE="$HOME/.gradle/wrapper/dists/gradle-9.6.1-bin/4ticwg1pgcbps2hj28r8so764/gradle-9.6.1/bin/gradle"
export JAVA_HOME=/home/tim/.gradle/jdks/eclipse_adoptium-21-amd64-linux.2
PORT=25607

mkdir -p "$SRV/mods" "$SRV/config"
for f in fabric-server-launch.jar eula.txt server.properties; do cp "$MOD/run/$f" "$SRV/"; done
[ -e "$SRV/libraries" ] || ln -s ../../run/libraries "$SRV/libraries"
[ -e "$SRV/versions" ] || ln -s ../../run/versions "$SRV/versions"
[ -e "$SRV/.fabric" ] || ln -s ../../run/.fabric "$SRV/.fabric"
rm -rf "$SRV/world"
find "$SRV/mods" -name '*.jar' -delete; cp "$MOD/build/libs/beyond-1.0.0.jar" "$SRV/mods/"
sed -i "s/^server-port=.*/server-port=$PORT/; s/^online-mode=.*/online-mode=false/; s/^spawn-protection=.*/spawn-protection=0/" "$SRV/server.properties"
grep -q "^online-mode=" "$SRV/server.properties" || echo "online-mode=false" >> "$SRV/server.properties"
cat > "$SRV/config/beyond.json" <<JSON
{ "pack_required": false, "pack_offer_on_join": false, "log_events": true }
JSON
echo '[{"uuid":"2474819f-b90f-3892-b735-07407c3c3e92","name":"ShotRig","level":4,"bypassesPlayerLimit":false}]' > "$SRV/ops.json"
rm -f "$SRV/console.fifo"; mkfifo "$SRV/console.fifo"
( cd "$SRV" && java -Xmx2G -jar fabric-server-launch.jar nogui < console.fifo > server.log 2>&1 ) &
SERVER_PID=$!
exec 3> "$SRV/console.fifo"
cleanup() { echo "stop" >&3 2>/dev/null; wait $SERVER_PID 2>/dev/null; exec 3>&- 2>/dev/null; rm -f "$SRV/console.fifo"; }
trap cleanup EXIT
for i in $(seq 1 240); do grep -q 'Done (' "$SRV/server.log" 2>/dev/null && break; sleep 1; done
grep -q 'Done (' "$SRV/server.log" || { echo "server did not boot"; tail -20 "$SRV/server.log"; exit 1; }
echo "gamerule spawn_mobs false" >&3

ls "$XDG_RUNTIME_DIR/wl-mc" >/dev/null 2>&1 || { weston --backend=headless --xwayland --socket=wl-mc --width=1920 --height=1080 --idle-time=0 > "$DIR/weston.log" 2>&1 & sleep 4; }
cp "$MOD/release/BeyondTheEnd-Music.zip" "$DIR/run/resourcepacks/" 2>/dev/null
rm -rf "$DIR/run/screenshots"; mkdir -p "$DIR/run/screenshots"
timeout 900 "$GRADLE" -p "$DIR" runClient -q "-Pcwrig=$DIR/${SCRIPT:-script.txt}|127.0.0.1:$PORT|:1|wl-mc" > "$DIR/runclient.log" 2>&1
echo "client exit $?"
mkdir -p "$DIR/shots"; rm -f "$DIR"/shots/*.png
cp "$DIR"/run/screenshots/*.png "$DIR/shots/" 2>/dev/null
echo "$(ls "$DIR"/shots/*.png 2>/dev/null | wc -l) screenshots in $DIR/shots"
grep -a -E "script:|screenshot|connecting|Exception|crashed" "$DIR/runclient.log" | grep -v "JAVA_TOOL\|Realms" | tail -12 | cut -c1-200
grep -E "River carved|Structure placed|EVENT|Loaded|Boss" "$SRV/server.log" | cut -c1-160 | tail -20
