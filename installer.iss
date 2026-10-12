[Setup]
AppName=NowPiano
AppVersion=1.0
AppVerName=NowPiano 1.0
AppPublisher=NowPiano
DefaultDirName={autopf}\NowPiano
DefaultGroupName=NowPiano
OutputDir=C:\NowPiano\installer_output
OutputBaseFilename=NowPiano_Setup_v1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\NowPiano.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "C:\NowPiano\src\dist\NowPiano\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NowPiano"; Filename: "{app}\NowPiano.exe"
Name: "{group}\Uninstall NowPiano"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NowPiano"; Filename: "{app}\NowPiano.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NowPiano.exe"; Description: "Launch NowPiano"; Flags: nowait postinstall skipifsilent
