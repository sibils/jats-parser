#!/usr/bin/env bash
# start / stop / status of the sibils api proxy server (sibils.v3/sibils_api_proxy_server.py)
# which fetches publications from biodiversitypmc.sibils.org and can build the PAM format locally.
#
# usage: ./pam_proxy.sh start|stop|restart|status|log
#
# example request once started:
#   curl 'http://localhost:8089/sibils/api/fetch?col=pmc&format=PAM&ids=PMC4909023'
#   (col: pmc, medline, plazi, zenodo, suppdata)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/sibils.v3"
SERVER="sibils_api_proxy_server.py"
PORT=8089                                   # hard coded in $SERVER
PID_FILE="$SCRIPT_DIR/tmp/pam_proxy.pid"
LOG_FILE="$SCRIPT_DIR/tmp/pam_proxy.log"
PYTHON="${PYTHON:-python3}"

get_pid() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid="$(cat "$PID_FILE")"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "$pid"
        return 0
    fi
    rm -f "$PID_FILE"   # stale pid file
    return 1
}

start() {
    local pid
    if pid="$(get_pid)"; then
        echo "proxy already running (pid $pid, port $PORT)"
        return 0
    fi
    mkdir -p "$(dirname "$PID_FILE")"
    cd "$SERVER_DIR" || exit 1
    # -u: unbuffered output so the log is written live
    nohup "$PYTHON" -u "$SERVER" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    if pid="$(get_pid)"; then
        echo "proxy started (pid $pid, port $PORT, log $LOG_FILE)"
    else
        echo "proxy failed to start, last log lines:"
        tail -n 20 "$LOG_FILE"
        return 1
    fi
}

stop() {
    local pid
    if ! pid="$(get_pid)"; then
        echo "proxy not running"
        return 0
    fi
    kill "$pid"
    for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo "proxy did not stop, sending SIGKILL"
        kill -9 "$pid"
    fi
    rm -f "$PID_FILE"
    echo "proxy stopped (pid $pid)"
}

status() {
    local pid
    if pid="$(get_pid)"; then
        echo "proxy running (pid $pid, port $PORT, log $LOG_FILE)"
        local code
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$PORT/ping" || true)"
        # any http answer (even 400 for an unknown path) means the server listens
        if [ -n "$code" ] && [ "$code" != "000" ]; then
            echo "port $PORT responding"
        else
            echo "WARNING: port $PORT not responding"
            return 1
        fi
    else
        echo "proxy not running"
        return 3
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; start ;;
    status)  status ;;
    log)     tail -n 50 -f "$LOG_FILE" ;;
    *)       echo "usage: $0 start|stop|restart|status|log"; exit 2 ;;
esac
