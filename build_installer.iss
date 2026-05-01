[Setup]
AppName=LeMoVi (Lehnin Molecule Visualizer)
AppVersion=1.0
AppPublisher=LeMoVi Team
DefaultDirName={autopf}\LeMoVi
DefaultGroupName=LeMoVi
OutputDir=Installer
OutputBaseFilename=LeMoVi_Installer
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=compiler:SetupClassicIcon.ico

[Files]
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "create_portable_python.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_de.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "Ideen.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "3Dmol-min.js"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "portable_python\*"; DestDir: "{app}\portable_python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ketcher\*"; DestDir: "{app}\ketcher"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "xtb\*"; DestDir: "{app}\xtb"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LeMoVi"; Filename: "{app}\start.bat"; IconFilename: "{app}\portable_python\WPy64-31180\python-3.11.8.amd64\pythonw.exe"
Name: "{autodesktop}\LeMoVi"; Filename: "{app}\start.bat"; IconFilename: "{app}\portable_python\WPy64-31180\python-3.11.8.amd64\pythonw.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
