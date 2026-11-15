#!/usr/bin/env bash
# IWD chapter-1 driver with automatic relaunch: runs tools/ieap_box.sh iwd-ch1; when the game dies before DONE
# (known issue: a crash while loading a map after a teleport), it relaunches from the autosave the game wrote just
# before (module Save/SlotAuto + its .iev variables) at the step that was running. Up to RELAUNCH (2) times.
# usage: tools/ieap_ch1.sh TAG [SECS]      env: IE_OUT (default /workspace/scratch/ieap), others as ieap_box.sh
set -u
TAG=${1:-ch1}; SECS=${2:-900}; HERE=$(cd "$(dirname "$0")" && pwd)
IE_OUT=${IE_OUT:-/workspace/scratch/ieap}; export IE_OUT STOP_ON_EXIT=1
OVERLAY=${OVERLAY:-/home/box/games/ToEE-ie}; SAVE=$OVERLAY/modules/IWD/Save
# (IWDAP_CH1_FROM + SAVES set by the caller: start with a resume)
for try in 0 $(seq 1 ${RELAUNCH:-2}); do
  t=$TAG; [ "$try" -gt 0 ] && t=$TAG-r$try
  "$HERE/ieap_box.sh" iwd-ch1 "$t" "$SECS"
  L=$IE_OUT/ingame/$t/probe.log; [ -f "$L" ] || L=$IE_OUT/ingame/probe.log
  grep -q '^DONE' "$L" 2>/dev/null && { grep -E '^SUMMARY' "$L"; exit 0; }
  step=$(grep -oE '^STEP [a-z0-9]+ n=1 ' "$L" | tail -1 | cut -d' ' -f2)
  [ -n "$step" ] && [ -e "$SAVE/SlotAuto.tfai" ] || { echo "ieap_ch1: no step / autosave to resume from"; exit 1; }
  [ -f "$IE_OUT/ingame/probe.log" ] && mkdir -p "$IE_OUT/ingame/$t" && mv -f "$IE_OUT/ingame/probe.log" "$IE_OUT/ingame/$t/"
  R=$IE_OUT/ingame/$t-resume; rm -rf "$R"; mkdir -p "$R"; cp -a "$SAVE"/SlotAuto* "$R/"
  echo "ieap_ch1: game ended before DONE in step $step: relaunch from its autosave"
  export IWDAP_CH1_FROM=$step SAVES=$R
done
echo "ieap_ch1: gave up after ${RELAUNCH:-2} relaunches"; exit 1
