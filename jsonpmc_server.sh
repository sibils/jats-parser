#!/usr/bin/env bash
# start / stop / status of the JATS parser http server (jsonpmc_httpserver.py)
# which retrieves PMC publications and parses them locally with process_xml.py.
#
# usage: ./jsonpmc_server.sh start|stop|restart|status|log
#
# example request once started:
#   curl 'http://localhost:8088/parse/pmc/3507161'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="jsonpmc_httpserver.py"
PORT=8088                                   # hard coded in $SERVER
PID_FILE="$SCRIPT_DIR/tmp/jsonpmc_server.pid"
LOG_FILE="$SCRIPT_DIR/tmp/jsonpmc_server.log"
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

port_responds() {
    local code
    # /annot/pmc/ does no retrieval or parsing, and any http answer means the server listens
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$PORT/annot/pmc/ping" || true)"
    [ -n "$code" ] && [ "$code" != "000" ]
}

start() {
    local pid
    if pid="$(get_pid)"; then
        echo "server already running (pid $pid, port $PORT)"
        return 0
    fi
    if port_responds; then
        echo "port $PORT is already in use by a process not started with this script, server not started"
        return 1
    fi
    mkdir -p "$(dirname "$PID_FILE")"
    # the server caches files in tmp/, relative to the current directory
    cd "$SCRIPT_DIR" || exit 1
    # -u: unbuffered output so the log is written live
    # PYTHONPATH: pmca_formatter.py is in sibils.v3/ (the symlink at the root is git ignored)
    PYTHONPATH="$SCRIPT_DIR/sibils.v3${PYTHONPATH:+:$PYTHONPATH}" \
        nohup "$PYTHON" -u "$SERVER" >> "$LOG_FILE" 2>&1 &
    pid=$!
    echo "$pid" > "$PID_FILE"
    # loading the python modules can take a few seconds
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if ! get_pid > /dev/null; then break; fi
        if port_responds; then
            echo "server started (pid $pid, port $PORT, log $LOG_FILE)"
            return 0
        fi
        sleep 1
    done
    if get_pid > /dev/null; then
        echo "server running (pid $pid) but port $PORT not responding yet, check the log: $LOG_FILE"
    else
        echo "server failed to start, last log lines:"
        tail -n 20 "$LOG_FILE"
    fi
    return 1
}

stop() {
    local pid
    if ! pid="$(get_pid)"; then
        echo "server not running"
        return 0
    fi
    kill "$pid"
    for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo "server did not stop, sending SIGKILL"
        kill -9 "$pid"
    fi
    rm -f "$PID_FILE"
    echo "server stopped (pid $pid)"
}

status() {
    local pid
    if pid="$(get_pid)"; then
        echo "server running (pid $pid, port $PORT, log $LOG_FILE)"
        if port_responds; then
            echo "port $PORT responding"
        else
            echo "WARNING: port $PORT not responding"
            return 1
        fi
    elif port_responds; then
        echo "server not started with this script, but port $PORT is responding"
        return 1
    else
        echo "server not running"
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
