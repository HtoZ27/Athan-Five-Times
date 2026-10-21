#!/usr/bin/env bash
# Isolated end-to-end tests for the tray backends (no real desktop involved).
#
# Scenarios (each inside its own private session bus via dbus-run-session):
#   no-host : detect_tray_kind() must be null
#   xapp    : mock org.x.StatusIconMonitor -> XApp backend registers its icon,
#             panel ButtonPress clicks arrive, tooltip updates travel the bus
#   sni     : mock StatusNotifierWatcher under Xephyr -> Qt backend registers,
#             an Activate call arrives
#
# Usage: scripts/e2e-tray-envs.sh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
MOCKS="$ROOT/scripts/e2e-tray-mocks.py"
XEMBED="$ROOT/scripts/e2e-tray-xembed.py"
DRIVER="$ROOT/scripts/e2e-tray.py"

PASSED=0
FAILURES=0

log()  { printf '* %s\n' "$*"; }
ok()   { PASSED=$((PASSED + 1)); printf 'PASS: %s\n' "$*"; }
fail() { FAILURES=$((FAILURES + 1)); printf 'FAIL: %s\n' "$*" >&2; }

wait_for() {  # wait_for <seconds> <condition...>
  local secs=$1 i
  shift
  for i in $(seq 1 "$((secs * 10))"); do
    if "$@"; then return 0; fi
    sleep 0.1
  done
  return 1
}

file_has() { [ -s "$1" ] && grep -q "$2" "$1"; }

json_field() {  # json_field <file> <key>
  "$PY" -c "import json,sys;d=json.load(open('$1'));print(d['$2'])" 2>/dev/null
}

# ── child scenarios ────────────────────────────────────────────────────────

scenario_no_host() {
  local dir ready log
  dir=$(mktemp -d)
  ready="$dir/ready.json"
  log="$dir/driver.log"
  if ! "$PY" "$DRIVER" --kind auto --duration 1 --ready-file "$ready" >"$log" 2>&1; then
    fail "no-host: driver exited nonzero: $(tail -n 3 "$log")"
    return
  fi
  if [ "$(json_field "$ready" kind)" = "None" ] && [ "$(json_field "$ready" hosted)" = "False" ]; then
    ok "no-host: detect_tray_kind() is null"
  else
    fail "no-host: unexpected ready file: $(cat "$ready")"
  fi
}

scenario_xapp() {
  local dir mon drv ready log monlog pid svc
  dir=$(mktemp -d)
  ready="$dir/ready.json"; log="$dir/driver.log"; monlog="$dir/monitor.log"

  "$PY" "$MOCKS" --monitor >"$monlog" 2>&1 &
  mon=$!
  trap 'kill "$mon" 2>/dev/null' RETURN

  if ! wait_for 5 file_has "$monlog" MONITOR_READY; then
    fail "xapp: mock monitor did not start: $(cat "$monlog")"
    return
  fi

  timeout 20 "$PY" "$DRIVER" --kind xapp --duration 8 --ready-file "$ready" >"$log" 2>&1 &
  drv=$!

  if ! wait_for 10 test -s "$ready"; then
    fail "xapp: driver never became ready: $(tail -n 3 "$log")"
    kill "$drv" 2>/dev/null
    return
  fi
  if [ "$(json_field "$ready" kind)" != "xapp" ] || [ "$(json_field "$ready" hosted)" != "True" ]; then
    fail "xapp: unexpected ready file: $(cat "$ready")"
    kill "$drv" 2>/dev/null
    return
  fi
  ok "xapp: backend registered and is_hosted() is True"
  pid=$(json_field "$ready" pid)
  svc="org.x.StatusIcon.athan$pid"

  if busctl --user call "$svc" /org/x/StatusIcon org.freedesktop.DBus.ObjectManager \
      GetManagedObjects 2>/dev/null | grep -q '/org/x/StatusIcon'; then
    ok "xapp: GetManagedObjects exposes the icon object"
  else
    fail "xapp: GetManagedObjects via busctl failed"
  fi

  if wait_for 6 sh -c "busctl --user get-property '$svc' /org/x/StatusIcon/Icon \
      org.x.StatusIcon TooltipText 2>/dev/null | grep -q 'e2e tooltip updated'"; then
    ok "xapp: tooltip property updated on the bus"
  else
    fail "xapp: tooltip property never updated"
  fi

  if busctl --user call "$svc" /org/x/StatusIcon/Icon org.x.StatusIcon \
      ButtonPress iiuui 250 250 1 0 0 2>/dev/null; then
    if wait_for 4 file_has "$log" "EVENT ACTIVATE"; then
      ok "xapp: left click (ButtonPress 1) raises activateRequested"
    else
      fail "xapp: left click did not reach the backend"
    fi
  else
    fail "xapp: ButtonPress call failed"
  fi

  busctl --user call "$svc" /org/x/StatusIcon/Icon org.x.StatusIcon \
      ButtonPress iiuui 250 250 3 0 0 >/dev/null 2>&1
  if wait_for 4 file_has "$log" "EVENT MENU"; then
    ok "xapp: right click (ButtonPress 3) raises menuRequested"
  else
    fail "xapp: right click did not reach the backend"
  fi

  wait "$drv"
  if file_has "$log" "STATE hosted=True" && file_has "$log" "EVENT done"; then
    ok "xapp: backend stayed hosted until shutdown"
  else
    fail "xapp: driver log tail: $(tail -n 3 "$log")"
  fi
}

scenario_sni() {
  local disp=$1 dir wat drv ready log watlog name
  dir=$(mktemp -d)
  ready="$dir/ready.json"; log="$dir/driver.log"; watlog="$dir/watcher.log"

  "$PY" "$MOCKS" --watcher >"$watlog" 2>&1 &
  wat=$!
  trap 'kill "$wat" 2>/dev/null' RETURN

  if ! wait_for 5 file_has "$watlog" WATCHER_READY; then
    fail "sni: mock watcher did not start: $(cat "$watlog")"
    return
  fi

  timeout 20 env DISPLAY="$disp" QT_QPA_PLATFORM=xcb \
    "$PY" "$DRIVER" --kind qt --duration 8 --ready-file "$ready" >"$log" 2>&1 &
  drv=$!

  if ! wait_for 10 test -s "$ready"; then
    fail "sni: driver never became ready: $(tail -n 3 "$log")"
    kill "$drv" 2>/dev/null
    return
  fi
  if [ "$(json_field "$ready" kind)" != "qt" ] || [ "$(json_field "$ready" hosted)" != "True" ]; then
    fail "sni: unexpected ready file: $(cat "$ready")"
    kill "$drv" 2>/dev/null
    return
  fi
  ok "sni: Qt backend registered and is_hosted() is True"

  if wait_for 5 file_has "$watlog" "REGISTER_ITEM"; then
    ok "sni: watcher received RegisterStatusNotifierItem"
  else
    fail "sni: watcher never saw a registration"
  fi

  # Qt 6 registers the item on its session-bus connection and passes the
  # object path to the watcher, so the sender's unique name is the owner.
  # Older Qt/KDE clients register a well-known org.kde.StatusNotifierItem-*
  # name instead; accept both.
  name=""; path="/StatusNotifierItem"
  if wait_for 5 file_has "$watlog" "REGISTER_ITEM"; then
    read -r _ name path <<<"$(grep -m1 '^REGISTER_ITEM ' "$watlog" | head -n 1)"
  fi
  if [ -z "$name" ]; then
    if wait_for 2 sh -c 'busctl --user list --no-legend 2>/dev/null | grep -q "^org\.kde\.StatusNotifierItem"' >/dev/null 2>&1; then
      name=$(busctl --user list --no-legend 2>/dev/null | grep -o "^org\.kde\.StatusNotifierItem[^ ]*" | head -n 1)
    fi
  fi
  if [ -z "$name" ]; then
    fail "sni: no StatusNotifierItem owner on the bus"
  else
    busctl --user call "$name" "$path" org.kde.StatusNotifierItem \
        Activate ii 0 0 >/dev/null 2>&1
    if wait_for 4 file_has "$log" "EVENT ACTIVATE"; then
      ok "sni: Activate on the SNI item raises activateRequested"
    else
      fail "sni: Activate did not reach the backend"
    fi
  fi

  wait "$drv"
  if file_has "$log" "STATE hosted=True" && file_has "$log" "EVENT done"; then
    ok "sni: backend stayed hosted until shutdown"
  else
    fail "sni: driver log tail: $(tail -n 3 "$log")"
  fi
}

scenario_xembed() {
  local disp=$1 dir mgr drv ready log mgrlog
  dir=$(mktemp -d)
  ready="$dir/ready.json"; log="$dir/driver.log"; mgrlog="$dir/manager.log"

  "$PY" "$XEMBED" --display "$disp" >"$mgrlog" 2>&1 &
  mgr=$!
  trap 'kill "$mgr" 2>/dev/null' RETURN

  if ! wait_for 5 file_has "$mgrlog" XEMBED_READY; then
    fail "xembed: mock tray manager did not start: $(cat "$mgrlog")"
    return
  fi

  timeout 20 env DISPLAY="$disp" QT_QPA_PLATFORM=xcb \
    "$PY" "$DRIVER" --kind auto --duration 6 --ready-file "$ready" >"$log" 2>&1 &
  drv=$!

  if ! wait_for 10 test -s "$ready"; then
    fail "xembed: driver never became ready: $(tail -n 3 "$log")"
    kill "$drv" 2>/dev/null
    return
  fi
  if [ "$(json_field "$ready" kind)" != "qt" ] || [ "$(json_field "$ready" hosted)" != "True" ]; then
    fail "xembed: unexpected ready file: $(cat "$ready")"
    kill "$drv" 2>/dev/null
    return
  fi
  ok "xembed: detect_tray_kind() picked Qt and is_hosted() is True"

  if wait_for 5 file_has "$mgrlog" DOCK; then
    ok "xembed: tray manager received the dock request"
  else
    fail "xembed: no dock request from QSystemTrayIcon"
  fi

  wait "$drv"
  if file_has "$log" "STATE hosted=True" && file_has "$log" "EVENT done"; then
    ok "xembed: backend stayed hosted until shutdown"
  else
    fail "xembed: driver log tail: $(tail -n 3 "$log")"
  fi
}

finish() {
  printf '\n%s passed, %s failed\n' "$PASSED" "$FAILURES"
  [ "$FAILURES" -eq 0 ]
}

# ── parent orchestration ───────────────────────────────────────────────────

x_display_ok() { xdpyinfo -display "$1" >/dev/null 2>&1; }

start_xephyr() {
  local d pid
  for d in 97 96 95 94; do
    Xephyr ":$d" -screen 800x600 -noreset >/dev/null 2>&1 &
    pid=$!
    if wait_for 8 x_display_ok ":$d"; then
      XEPHYR_DISPLAY=":$d"
      XEPHYR_PID=$pid
      return 0
    fi
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
  done
  return 1
}

main() {
  command -v dbus-run-session >/dev/null || { echo "dbus-run-session is required" >&2; exit 2; }
  command -v busctl >/dev/null || { echo "busctl is required" >&2; exit 2; }
  command -v xdpyinfo >/dev/null || { echo "xdpyinfo is required" >&2; exit 2; }
  "$PY" -c "import dbus, gi" 2>/dev/null || {
    echo "python3-dbus and PyGObject are required" >&2; exit 2; }

  log "scenario: no host (private bus)"
  if dbus-run-session -- "$0" --scenario-no-host; then :; else fail "scenario no-host"; fi

  log "scenario: XApp StatusIcon host (private bus)"
  if dbus-run-session -- "$0" --scenario-xapp; then :; else fail "scenario xapp"; fi

  log "scenario: SNI host under Xephyr (private bus)"
  if start_xephyr; then
    if dbus-run-session -- "$0" --scenario-sni "$XEPHYR_DISPLAY"; then :; else fail "scenario sni"; fi
    log "scenario: classic XEmbed tray (private bus, Xephyr)"
    if dbus-run-session -- "$0" --scenario-xembed "$XEPHYR_DISPLAY"; then :; else fail "scenario xembed"; fi
    kill "$XEPHYR_PID" 2>/dev/null
  else
    fail "could not start Xephyr"
  fi

  printf '\n=== %s scenario checks failed ===\n' "$FAILURES"
  [ "$FAILURES" -eq 0 ]
}

case "${1:-}" in
  --scenario-no-host) scenario_no_host; finish ;;
  --scenario-xapp)    scenario_xapp; finish ;;
  --scenario-sni)     shift; scenario_sni "$1"; finish ;;
  --scenario-xembed)  shift; scenario_xembed "$1"; finish ;;
  *)                  main ;;
esac
