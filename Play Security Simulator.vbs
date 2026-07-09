Set shell = CreateObject("WScript.Shell")
gameDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
bat = Chr(34) & gameDir & "\Play Security Simulator.bat" & Chr(34)
shell.Run bat, 0, True
