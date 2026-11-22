Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
localAppData = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
appScript = scriptDir & "\app_gui.py"

pythonwPath = localAppData & "\Python\bin\pythonw.exe"

If objFSO.FileExists(pythonwPath) Then
    objShell.Run Chr(34) & pythonwPath & Chr(34) & " " & Chr(34) & appScript & Chr(34), 0, False
Else
    objShell.Run "pythonw.exe " & Chr(34) & appScript & Chr(34), 0, False
End If
