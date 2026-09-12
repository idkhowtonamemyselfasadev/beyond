#!/bin/bash
cd "$(dirname "$0")" || exit 1
PID=run.pid
stop() {
    if [ -f $PID ] && kill -0 "$(cat $PID)" 2>/dev/null; then
        kill "$(cat $PID)"
        for _ in $(seq 1 60); do kill -0 "$(cat $PID)" 2>/dev/null || break; sleep 1; done
        kill -9 "$(cat $PID)" 2>/dev/null
    fi
    rm -f $PID
}
start() {
    mkdir -p mods
    rm -f mods/beyond-*.jar
    cp -f ../build/libs/beyond-1.1.0.jar mods/
    rm -f boot.log
    nohup java -Xms1G -Xmx3G -jar fabric-server-launch.jar nogui > boot.log 2>&1 &
    echo $! > $PID
    for _ in $(seq 1 180); do
        grep -qE 'Done \(|Failed to load|Registry loading errors' boot.log 2>/dev/null && break
        sleep 1
    done
    grep -E 'Beyond the End ready|Installed data pack|Done \(|Failed to load|Registry loading errors' boot.log | tail -4
}
case "$1" in
  stop) stop ;;
  fresh) stop; rm -rf world logs; start ;;
  restart) stop; start ;;
  *) start ;;
esac
