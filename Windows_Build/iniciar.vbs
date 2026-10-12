Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
sDir = fso.GetParentFolderName(WScript.ScriptFullName)
sParentDir = fso.GetParentFolderName(sDir)
oShell.CurrentDirectory = sParentDir
' Intentar lanzar con pythonw (sin ventana negra de consola)
ret = oShell.Run("cmd /c start """" pythonw """ & sParentDir & "\main.py""", 0, False)
Set oShell = Nothing
Set fso = Nothing
