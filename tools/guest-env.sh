source "$HOME/COMP3431/tools/env.sh"
# Maintenance commands inherit the active student's graphical session settings.
# Normal student terminals already contain these variables.
eval "$(python3 - <<'PY'
import os,pathlib,shlex
for p in pathlib.Path('/proc').glob('[0-9]*'):
 try:
  if p.stat().st_uid == os.getuid() and (p/'comm').read_text().strip() == 'gnome-shell':
   env=dict(x.split(b'=',1) for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x)
   for k in ('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'):
    if k.encode() in env:print('export '+k+'='+shlex.quote(env[k.encode()].decode()))
   break
 except (FileNotFoundError,PermissionError):pass
PY
)"
