@echo off
rem ie2toee quest-giver autoplayer tour on native Windows (the box runs tools/ieap_box.sh under Wine instead).
rem Put this file next to the AUTOPLAYER TemplePlus.exe (a separate folder, not your normal Temple+ install).
rem
rem usage: ieap.bat iwd|iwd2|iwd-ch1|iwd2-ch1 SAVE [GAMEDIR]
rem   iwd       IWD Easthaven tour   (AUTOPLAYER_SCENARIO=easthaven, module IWD)
rem   iwd2      IWD2 Targos tour     (AUTOPLAYER_SCENARIO=targos,    module ToEE)
rem   iwd-ch1   IWD new game -> prologue -> AR2000 (AUTOPLAYER_SCENARIO=iwd_ch1, module IWD). Use SAVE "menu":
rem             the driver starts the new game itself from the main menu with the pregenerated party. If the game
rem             crashes on the way (known: on the AR1006 re-entry), it is relaunched once or twice from the autosave.
rem   iwd2-ch1  IWD2 new game -> Shawford chain -> palisade -> Ulbrec (AUTOPLAYER_SCENARIO=iwd2_ch1, module ToEE). SAVE "menu".
rem   SAVE     the save to load: its file name without extension, e.g. slot0007 for modules\IWD\Save\slot0007.tfaf;
rem            or "menu": no autoload, load (or start) a game yourself and the tour begins once you are in it
rem   GAMEDIR  optional game folder, e.g. "D:\GOG Games\ToEEWindale". Given: TemplePlus.ini's toeeDir/defaultModule
rem            are pointed at it for this run and restored afterwards. Omitted: the ini is used as it is.
rem Output: IWDAP lines (RESULT PASS/FAIL/SKIP, ANOMALY, SUMMARY, TABLE) in ieap-<game>.log next to this file and in
rem %USERPROFILE%\Saved Games\TemplePlus\TemplePlus.log. Keep the game window focused while it runs.
setlocal
set "GAME=%~1"
set "SAVE=%~2"
set "GAMEDIR=%~3"
if /i "%GAME%"=="iwd"  (set "AUTOPLAYER_SCENARIO=easthaven" & set "MOD=IWD")
if /i "%GAME%"=="iwd2" (set "AUTOPLAYER_SCENARIO=targos" & set "MOD=ToEE")
if /i "%GAME%"=="iwd-ch1"  (set "AUTOPLAYER_SCENARIO=iwd_ch1" & set "MOD=IWD")
if /i "%GAME%"=="iwd2-ch1" (set "AUTOPLAYER_SCENARIO=iwd2_ch1" & set "MOD=ToEE")
if not defined MOD goto usage
if "%SAVE%"=="" goto usage
if not exist "%~dp0TemplePlus.exe" (echo no TemplePlus.exe next to %~nx0 & exit /b 1)
if /i not "%SAVE%"=="menu" set "TP_AUTOLOAD=%SAVE%"
set "TP_AUTOEXEC=from templeplus import autoplayer; autoplayer.play_new_game()"
set "IWDAP_LOG=%~dp0ieap-%GAME%.log"
if exist "%IWDAP_LOG%" move /y "%IWDAP_LOG%" "%IWDAP_LOG%.prev" >nul
set "INI=%USERPROFILE%\Saved Games\TemplePlus\TemplePlus.ini"
if not "%GAMEDIR%"=="" (
  if not exist "%GAMEDIR%\modules\%MOD%_core\scr" (echo no converted module in "%GAMEDIR%\modules\%MOD%_core" & exit /b 1)
  set "IE2TOEE_CORE=%GAMEDIR%\modules\%MOD%_core"
  copy /y "%INI%" "%INI%.ieap-backup" >nul
  powershell -NoProfile -Command "$p=$env:INI; $d=$env:GAMEDIR.TrimEnd('\') + '\'; (Get-Content -LiteralPath $p) -replace '^toeeDir=.*', ('toeeDir=' + $d) -replace '^defaultModule=.*', ('defaultModule=' + $env:MOD) | Set-Content -LiteralPath $p"
)
echo ieap: %GAME% (%AUTOPLAYER_SCENARIO%), module %MOD%, save %SAVE%, log %IWDAP_LOG%
set /a TRY=0
:run
pushd "%~dp0"
start "" /wait TemplePlus.exe
popd
rem the chapter drivers: the game ended before DONE (a crash) -> relaunch from the autosave at the step that was running
if /i not "%AUTOPLAYER_SCENARIO:~-3%"=="ch1" goto after
findstr /b "DONE" "%IWDAP_LOG%" >nul 2>&1 && goto after
if %TRY% geq 2 goto after
set "STEP="
for /f "tokens=2,3" %%a in ('findstr /b /c:"STEP " "%IWDAP_LOG%"') do if "%%b"=="n=1" set "STEP=%%a"
if not defined STEP goto after
set /a TRY+=1
echo ieap: the game ended in step %STEP% before DONE: relaunch %TRY% from the autosave
set "IWDAP_CH1_FROM=%STEP%"
set "TP_AUTOLOAD=SlotAuto"
copy /y "%IWDAP_LOG%" "%IWDAP_LOG%.try%TRY%" >nul
goto run
:after
if not "%GAMEDIR%"=="" move /y "%INI%.ieap-backup" "%INI%" >nul
if exist "%IWDAP_LOG%" findstr /b "RESULT SKIP ANOMALY SUMMARY TABLE" "%IWDAP_LOG%"
exit /b 0
:usage
echo usage: %~nx0 iwd^|iwd2^|iwd-ch1^|iwd2-ch1 SAVE [GAMEDIR]
exit /b 2
