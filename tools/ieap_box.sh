#!/usr/bin/env bash
# Box (Linux + Wine, private Xvfb) runner for the ie2toee quest-giver tours.  Windows: tools\ieap.bat instead.
# usage: tools/ieap_box.sh iwd|iwd2 TAG [SECS]
#   iwd  -> AUTOPLAYER_SCENARIO=easthaven, module IWD  (game folder $OVERLAY, default /home/box/games/ToEE-ie)
#   iwd2 -> AUTOPLAYER_SCENARIO=targos,    module ToEE (game folder $OVERLAY, default /workspace/scratch/ToEE-iwd2ap:
#           a symlink copy of vanilla ToEE with an IWD2 convert installed over it)
# env: TP_DIST (Temple+ autoplayer dist), TP_AUTOLOAD (save to load, default SlotAuto from $SAVES), SAVES (folder with
#      that save, default the vanilla harness saves), RUN_INGAME (the probe-loop runner from ie2toee proto/), IWDAP_* switches.
# Points the prefix's TemplePlus.ini (toeeDir, defaultModule) at the game folder for the run and restores it afterwards.
set -u
GAME=${1:?iwd or iwd2}; TAG=${2:-run}; SECS=${3:-600}
case "$GAME" in
  iwd)  SCEN=easthaven; MODULE=IWD;  OVERLAY=${OVERLAY:-/home/box/games/ToEE-ie} ;;
  iwd-ch1) SCEN=iwd_ch1; MODULE=IWD; OVERLAY=${OVERLAY:-/home/box/games/ToEE-ie} ;;   # new game -> AR2000 (scr/iwd_ch1_driver.py)
  iwd2) SCEN=targos;    MODULE=ToEE; OVERLAY=${OVERLAY:-/workspace/scratch/ToEE-iwd2ap} ;;
  *) echo "usage: $0 iwd|iwd-ch1|iwd2 TAG [SECS]" >&2; exit 2 ;;
esac
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine-toee-ie}
export TP_DIST=${TP_DIST:-/workspace/tp-build/dist-autoplayer-iwd2}
export TOEE_DIR=${TOEE_DIR:-/home/box/games/ToEE-preview}   # run_ingame restores modules/ToEE/Save from here
export TOEE_OVERLAY=$OVERLAY IE_OUT=${IE_OUT:-/workspace/scratch/ieap} TOEE_XVFB=${TOEE_XVFB:-7}
RUN_INGAME=${RUN_INGAME:-/workspace/ie-import/proto/run_ingame.sh}
SAVES=${SAVES:-$TOEE_DIR/modules/ToEE/Save}
CORE=$OVERLAY/modules/${MODULE}_core
[ -d "$CORE/scr" ] || { echo "no converted module scripts in $CORE" >&2; exit 1; }
mkdir -p "$IE_OUT/ingame"
export IWDAP_IGNORE_FOCUS=1 AUTOPLAYER_SCENARIO=$SCEN IE2TOEE_CORE="Z:$CORE" IWDAP_LOG="Z:$IE_OUT/ingame/probe.log"
export TP_AUTOEXEC="from templeplus import autoplayer; autoplayer.play_new_game()"
export TP_AUTOLOAD=${TP_AUTOLOAD:-SlotAuto}
if [ "$MODULE" != ToEE ]; then   # the harness save must be in the module's own Save folder: refreshed from the vanilla
  # one every run (the probes' autosaves overwrite it with pickled time events of modules a later run can't import)
  mkdir -p "$OVERLAY/modules/$MODULE/Save"; rm -f "$OVERLAY/modules/$MODULE/Save/$TP_AUTOLOAD".iev
  for f in "$SAVES/$TP_AUTOLOAD".* "$SAVES/$TP_AUTOLOAD"*.gsi; do cp -a "$f" "$OVERLAY/modules/$MODULE/Save/"; done
fi
NAME=$(basename "$OVERLAY"); LINK="$WINEPREFIX/drive_c/GOG Games/$NAME"
[ -e "$LINK" ] || ln -s "$OVERLAY" "$LINK"
INI="$WINEPREFIX/drive_c/users/$USER/Saved Games/TemplePlus/TemplePlus.ini"; BAK="$INI.ieap-backup"
[ -e "$BAK" ] || cp "$INI" "$BAK"      # a leftover backup (crashed run) is the true original: keep it
trap 'mv -f "$BAK" "$INI"' EXIT
sed -i "s|^toeeDir=.*|toeeDir=C:\\\\GOG Games\\\\$NAME\\\\|; s|^defaultModule=.*|defaultModule=$MODULE|" "$INI"
echo "ieap: $GAME ($SCEN) module $MODULE in C:\\GOG Games\\$NAME, dist $TP_DIST, save $TP_AUTOLOAD"
# own private Xvfb (its log and exit status kept: on Nov 15 the display died twice right after a conversation)
XLOG="$IE_OUT/ingame/xvfb-$TAG.log"
( Xvfb ":$TOEE_XVFB" -screen 0 1300x840x24 +extension GLX -nolisten tcp > "$XLOG" 2>&1; echo "Xvfb exited with status $? at $(date +%T)" >> "$XLOG" ) &
export DISPLAY=":$TOEE_XVFB"; XN=$TOEE_XVFB; unset TOEE_XVFB; sleep 1
trap 'mv -f "$BAK" "$INI"; pkill -u "$USER" -f "^Xvfb :$XN " 2>/dev/null' EXIT
SNAPPER=
if [ -n "${SNAP:-}" ]; then   # SNAP=<secs>: a screenshot of the virtual display every <secs> s (diagnosing stalls)
  mkdir -p "$IE_OUT/ingame/$TAG"
  ( i=0; while sleep "$SNAP"; do i=$((i+1)); import -display ":$XN" -window root -resize 50% "$IE_OUT/ingame/$TAG/snap_$(printf %03d $i).jpg" 2>/dev/null; done ) & SNAPPER=$!
fi
( cd "$(dirname "$RUN_INGAME")" && ./"$(basename "$RUN_INGAME")" "$TAG" "$SECS" )
[ -n "$SNAPPER" ] && kill "$SNAPPER" 2>/dev/null
grep -E '^(RESULT|SKIP|ANOMALY|SUMMARY|TABLE|TALK|GOTO|HOP)' "$IE_OUT/ingame/$TAG/probe.log" 2>/dev/null | cut -c1-240
