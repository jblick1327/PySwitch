[Setup]
AppName=SwitchInterface
AppVersion={version}
AppPublisher=Open-Source AT
DefaultDirName={localappdata}\SwitchInterface
OutputBaseFilename=SwitchInterface-{version}
PrivilegesRequired=lowest
DefaultGroupName=SwitchInterface

[Files]
Source: "{exe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\SwitchInterface"; Filename: "{app}\SwitchInterface.exe"
Name: "{group}\SwitchInterface"; Filename: "{app}\SwitchInterface.exe"
