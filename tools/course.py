#!/usr/bin/env python3
"""Student commands for the isolated local simulation. Ubuntu/ROS2 Humble."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path.home() / 'COMP3431'
STATE = ROOT / '.course'
STATE.mkdir(exist_ok=True)
FILE = STATE / 'session.json'


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {}


def save(data):
    temp = FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(FILE)


def members(data, name=None):
    """Select by UID and unpredictable session tag, even if launch has exited."""
    result = []
    if not data.get('token'):
        return result
    tag = ('COMP3431_SESSION=' + data['token']).encode()
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if p.stat().st_uid != os.getuid():
                continue
            env = (p / 'environ').read_bytes().split(b'\0')
            if tag in env and (name is None or ('COMP3431_COMPONENT=' + name).encode() in env):
                result.append(int(p.name))
        except (OSError, ValueError):
            pass
    return result


def spawn(data, name, argv):
    env = dict(os.environ, COMP3431_SESSION=data['token'], COMP3431_COMPONENT=name,
               ROS_LOG_DIR=str(Path(data['logs']) / 'ros'))
    with (Path(data['logs']) / (name + '.log')).open('a') as out:
        p = subprocess.Popen(argv, cwd=ROOT, env=env, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
    data.setdefault('processes', {})[name] = p.pid
    save(data)


def executable_running(data, name):
    for pid in members(data):
        try:
            if (Path('/proc') / str(pid) / 'comm').read_text().strip() == name:
                return True
        except OSError:
            pass
    return False


def zero_velocity():
    subprocess.run(['ros2', 'topic', 'pub', '--once', '--wait-matching-subscriptions', '0',
                    '/cmd_vel', 'geometry_msgs/msg/Twist', '{}'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)


def stop(data, name=None):
    if not members(data, name):
        return
    if name is None or name == 'wall-follower':
        zero_velocity()
    for sig, seconds in ((signal.SIGINT, 5), (signal.SIGTERM, 3), (signal.SIGKILL, 1)):
        for pid in members(data, name):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        end = time.monotonic() + seconds
        while time.monotonic() < end and members(data, name):
            time.sleep(.2)
    if members(data, name):
        raise RuntimeError('A course process did not stop; see course status.')
    if name == 'wall-follower':
        zero_velocity()


def start(args):
    if args.profile is None:
        args.profile = 'standard' if args.mode == 'vision' else 'balanced'
    old = load()
    if members(old):
        raise RuntimeError('A course session is already running. Use course stop or course reset.')
    if args.mode == 'navigation' and (not args.map or not Path(args.map).expanduser().is_file()):
        raise RuntimeError('Navigation requires an existing map: --map ~/COMP3431/maps/my-map.yaml')
    if args.mode == 'vision' and args.profile != 'standard':
        raise RuntimeError('The supplied vision example assumes a 640-pixel image. Use standard for vision.')
    token = uuid.uuid4().hex
    logs = ROOT / 'logs' / (time.strftime('%Y%m%d-%H%M%S-') + token[:6])
    logs.mkdir(parents=True)
    data = {'token': token, 'logs': str(logs), 'mode': args.mode, 'profile': args.profile,
            'gui': args.gui, 'rviz': not args.no_rviz, 'map': str(Path(args.map).expanduser().resolve()) if args.map else ''}
    save(data)
    cmd = ['ros2', 'launch', 'turtlebot3_gazebo', 'course.launch.py',
           'mode:=' + data['mode'], 'profile:=' + data['profile'],
           'gui:=' + str(data['gui']).lower(), 'rviz:=' + str(data['rviz']).lower()]
    if data['map']:
        cmd.append('map:=' + data['map'])
    spawn(data, 'simulation', cmd)
    print('Starting', data['mode'], 'with', data['profile'], 'profile. Logs:', logs, flush=True)
    time.sleep(3)
    if not members(data):
        raise RuntimeError('Launch exited. Read ' + str(logs / 'simulation.log'))
    checked = subprocess.run([sys.executable, str(ROOT / 'tools/health.py'), '--live', '--seconds', '25',
                              '--camera', str(data['profile'] != 'mapping').lower(),
                              '--map', str(data['mode'] in ('mapping', 'vision')).lower()],
                             capture_output=True, text=True)
    (logs / 'startup-health.json').write_text(checked.stdout)
    if checked.stderr:
        (logs / 'startup-health-stderr.log').write_text(checked.stderr)
    rviz_alive = executable_running(data, 'rviz2')
    if checked.returncode or (data['rviz'] and not rviz_alive):
        stop(data)
        raise RuntimeError('Startup data or RViz check failed. The session was stopped. See ' + str(logs))
    if args.mode == 'navigation':
        print('Ready. In RViz set 2D Pose Estimate, then use Nav2 Goal. Initial pose is required.')
    else:
        print('Ready. The robot is stationary. Use course wall-follow or course teleop to move it.')


def main():
    p = argparse.ArgumentParser(description='COMP3431 local simulation and development')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('start', help='Start a stationary simulation and the selected exercise tools')
    s.add_argument('mode', nargs='?', choices=['mapping', 'vision', 'navigation'], default='mapping')
    s.add_argument('--profile', choices=['balanced', 'mapping', 'standard'], default=None)
    s.add_argument('--gui', action='store_true', help='Also display the Gazebo 3D window')
    s.add_argument('--no-rviz', action='store_true')
    s.add_argument('--map')
    for name in ('stop', 'status', 'reset', 'wall-follow', 'stop-robot', 'teleop', 'build'):
        sub.add_parser(name)
    d = sub.add_parser('doctor'); d.add_argument('--live', action='store_true')
    d.add_argument('--verbose', action='store_true', help='Print full diagnostic details')
    m = sub.add_parser('save-map'); m.add_argument('name')
    args = p.parse_args()
    # Serialise mutations; interactive teleop deliberately does not hold this lock.
    lock = (STATE / 'lock').open('w')
    if args.command not in ('teleop', 'doctor', 'status'):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = load()
    if args.command == 'start':
        start(args)
    elif args.command == 'status':
        print(json.dumps({'running': bool(members(data)), 'processes': members(data), **data}, indent=2))
    elif args.command == 'stop':
        stop(data); print('Course simulation stopped.')
    elif args.command == 'reset':
        if not data:
            raise RuntimeError('No previous course session. Use course start.')
        stop(data)
        start(argparse.Namespace(mode=data['mode'], profile=data['profile'], gui=data['gui'],
                                 no_rviz=not data['rviz'], map=data['map']))
    elif args.command == 'wall-follow':
        if not members(data) or data.get('mode') == 'navigation':
            raise RuntimeError('Start mapping or vision first. Wall following cannot run alongside Nav2.')
        if members(data, 'wall-follower'):
            raise RuntimeError('The wall follower is already running.')
        spawn(data, 'wall-follower', ['ros2', 'run', 'wall_follower', 'wall_follower',
                                      '--ros-args', '-p', 'use_sim_time:=true'])
        print('Wall follower started in local simulation. Stop with course stop-robot.')
    elif args.command == 'stop-robot':
        stop(data, 'wall-follower'); zero_velocity(); print('Wall follower stopped; zero velocity sent.')
        if data.get('mode') == 'navigation':
            print('Cancel an active Nav2 goal in RViz; use course stop to stop the entire session.')
    elif args.command == 'teleop':
        if not members(data) or data.get('mode') == 'navigation':
            raise RuntimeError('Start mapping or vision first; use Nav2 goals in navigation mode.')
        stop(data, 'wall-follower')
        try:
            subprocess.run(['ros2', 'run', 'turtlebot3_teleop', 'teleop_keyboard'])
        finally:
            zero_velocity()
    elif args.command == 'save-map':
        dest = Path(args.name).expanduser()
        if not dest.is_absolute():
            dest = ROOT / 'maps' / dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.with_suffix('.yaml').exists() or dest.with_suffix('.pgm').exists():
            raise RuntimeError('Map already exists. Choose a new name to preserve it.')
        subprocess.run(['ros2', 'run', 'nav2_map_server', 'map_saver_cli', '-f', str(dest),
                        '--ros-args', '-p', 'use_sim_time:=true', '-p', 'save_map_timeout:=20.0'], check=True)
    elif args.command == 'doctor':
        extra = ['--live', '--camera', str(data.get('profile') != 'mapping').lower(),
                 '--map', str(data.get('mode') in ('mapping', 'vision')).lower()] if args.live else []
        result = subprocess.run([sys.executable, str(ROOT / 'tools/health.py')] + extra,
                                capture_output=True, text=True)
        diagnostic = ROOT / 'logs' / 'doctor-latest.json'
        diagnostic.parent.mkdir(exist_ok=True)
        diagnostic.write_text(result.stdout + result.stderr)
        if args.verbose:
            print(result.stdout + result.stderr, end='')
        elif result.returncode == 0:
            print('PASS: ROS 2 Humble, course packages and development tools are ready.')
            if args.live:
                print('Live sensor data and required transforms passed.')
            print('Full diagnostic report:', diagnostic)
        else:
            print('A setup check failed. Full diagnostic report:', diagnostic, file=sys.stderr)
        sys.exit(result.returncode)
    elif args.command == 'build':
        if members(data):
            raise RuntimeError('Stop the course session before rebuilding.')
        env = {k: v for k, v in os.environ.items() if k not in (
            'AMENT_PREFIX_PATH', 'COLCON_PREFIX_PATH', 'CMAKE_PREFIX_PATH', 'PYTHONPATH', 'LD_LIBRARY_PATH')}
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c',
                        'source /opt/ros/humble/setup.bash && colcon build --symlink-install --executor sequential'],
                       cwd=ROOT, env=env, check=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, BlockingIOError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
