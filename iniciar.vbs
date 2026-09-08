Set oShell = CreateObject("WScript.Shell")
sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
oShell.CurrentDirectory = sDir
oShell.Run "pythonw """ & sDir & "\main.py""", 0, False
Set oShell = Nothing
