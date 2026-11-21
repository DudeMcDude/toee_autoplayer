// Windows Script Host supervisor for one TemplePlus chapter run.
var shell = new ActiveXObject('WScript.Shell');
var files = new ActiveXObject('Scripting.FileSystemObject');
var marker = shell.Environment('Process')('IWDAP_RESTART_FILE');
var engine = shell.Exec('"' + files.BuildPath(shell.CurrentDirectory, 'TemplePlus.exe') + '"');
while (engine.Status === 0) {
    WScript.Sleep(500);
    if (!files.FileExists(marker)) continue;
    var input = files.OpenTextFile(marker, 1);
    var request = /^(\d+) ([a-z][a-z0-9_]*)\s*$/.exec(input.ReadAll());
    input.Close();
    if (!request || Number(request[1]) !== engine.ProcessID) continue;
    // The driver has finished saving and stopped issuing actions. Close only this game.
    shell.Run('taskkill /PID ' + engine.ProcessID, 0, true);
    for (var i = 0; i < 12 && engine.Status === 0; ++i) WScript.Sleep(500);
    if (engine.Status === 0) engine.Terminate();
    WScript.Quit(75);
}
WScript.Quit(engine.ExitCode === 75 ? 1 : engine.ExitCode);
