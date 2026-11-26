#!/usr/bin/env python3
"""Check dependencies, then observe actual messages; never commands motion."""
import argparse
import json
import math
import subprocess
import os
from pathlib import Path
import platform
import shutil
import time

p = argparse.ArgumentParser()
p.add_argument('--live', action='store_true')
p.add_argument('--seconds', type=float, default=20)
p.add_argument('--camera', choices=['true', 'false'], default='true')
p.add_argument('--map', choices=['true', 'false'], default='true')
a = p.parse_args()
checks = {}
checks['architecture'] = platform.machine() == 'aarch64'
checks['ros_humble'] = os.environ.get('ROS_DISTRO') == 'humble'
checks['local_simulation'] = os.environ.get('ROS_LOCALHOST_ONLY') == '1' and os.environ.get('ROS_DOMAIN_ID') == '73'
for command in ('ros2', 'colcon', 'ign', 'rviz2', 'g++', 'git'):
    checks[command] = bool(shutil.which(command))
import cv2
from cv_bridge import CvBridge
from ament_index_python.packages import get_package_share_directory
for pkg in ('wall_follower', 'turtlebot3_gazebo', 'turtlebot3_cartographer', 'nav2_bringup', 'demo_nodes_cpp', 'demo_nodes_py'):
    try:
        checks[pkg] = Path(get_package_share_directory(pkg)).is_dir()
    except LookupError:
        checks[pkg] = False
details = {'opencv': cv2.__version__}
if os.environ.get('DISPLAY') and shutil.which('glxinfo'):
    g = subprocess.run(['glxinfo', '-B'], capture_output=True, text=True, timeout=15)
    details['graphics'] = g.stdout.strip()
    checks['graphics_context'] = g.returncode == 0
if a.live:
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, LaserScan
    from nav_msgs.msg import Odometry, OccupancyGrid
    from tf2_ros import Buffer, TransformListener
    rclpy.init()
    n = Node('comp3431_health', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buf = Buffer(); listener = TransformListener(buf, n)
    stamps = {}; counts = {}; last = {}
    def record(key, stamp):
        counts[key] = counts.get(key, 0) + 1
        stamps.setdefault(key, set()).add((stamp.sec, stamp.nanosec))
    def scan(m):
        record('scan', m.header.stamp)
        finite = [v for v in m.ranges if math.isfinite(v)]
        details['scan_min'] = min(finite, default=None)
        details['scan_max'] = max(finite, default=None)
        details['scan_beams'] = len(m.ranges)
    def camera(m):
        record('camera', m.header.stamp)
        if 'image_shape' not in details:
            details['image_shape'] = list(CvBridge().imgmsg_to_cv2(m, 'bgr8').shape)
    def grid(m):
        record('map', m.header.stamp)
        details['known_map_cells'] = sum(v >= 0 for v in m.data)
    subs = [n.create_subscription(Clock, '/clock', lambda m: record('clock', m.clock), qos_profile_sensor_data),
            n.create_subscription(LaserScan, '/scan', scan, qos_profile_sensor_data),
            n.create_subscription(Odometry, '/odom', lambda m: record('odom', m.header.stamp), qos_profile_sensor_data),
            n.create_subscription(Image, '/camera/rgb/image_raw', camera, qos_profile_sensor_data),
            n.create_subscription(OccupancyGrid, '/map', grid, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))]
    required = ['clock', 'scan', 'odom'] + (['camera'] if a.camera == 'true' else [])
    pairs = [('odom', 'base_footprint'), ('base_link', 'base_scan'), ('base_link', 'camera_link')]
    if a.map == 'true':
        pairs.append(('map', 'base_footprint'))
    start = time.monotonic()
    while time.monotonic() - start < a.seconds:
        rclpy.spin_once(n, timeout_sec=.1)
        if (time.monotonic() - start > 2 and all(len(stamps.get(k, set())) >= 3 for k in required)
            and all(buf.can_transform(x, y, rclpy.time.Time()) for x, y in pairs)
            and (a.map != 'true' or details.get('known_map_cells', 0) > 10)):
            break
    for key in required:
        checks['live_' + key] = len(stamps.get(key, set())) >= 3
    if a.map == 'true':
        checks['nonempty_map'] = details.get('known_map_cells', 0) > 10
    for x, y in pairs:
        checks['tf_' + x + '_' + y] = buf.can_transform(x, y, rclpy.time.Time())
    details['message_counts'] = counts
    details['elapsed_seconds'] = time.monotonic() - start
    n.destroy_node(); rclpy.shutdown()
result = {'passed': all(checks.values()), 'checks': checks, 'details': details}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
