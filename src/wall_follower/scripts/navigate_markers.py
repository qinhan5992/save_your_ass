#!/usr/bin/env python3

import csv
from math import atan2, cos, isfinite, sin
from pathlib import Path
from time import monotonic

import rclpy
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.srv import LoadMap
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.executors import ExternalShutdownException
from rclpy.signals import SignalHandlerOptions


def read_rows(path, expected):
    with path.open(newline='') as stream:
        rows = [row for row in csv.reader(stream, strict=True) if row]
    if len(rows) != expected or any(len(row) != 3 for row in rows):
        raise ValueError(f'{path} must contain {expected} rows of three values')
    values = [tuple(map(float, row)) for row in rows]
    if any(not isfinite(value) for row in values for value in row):
        raise ValueError(f'{path} contains a non-finite value')
    return values


def read_route(path, odom_matches_map=False):
    odom_start, *markers = read_rows(path, 5)
    map_start = odom_start
    if not odom_matches_map:
        saved_odom_start, map_start = read_rows(path.with_suffix('.start-map.csv'), 2)
        if odom_start != saved_odom_start:
            raise ValueError('Marker file and companion map start have different odometry starts')
    if any(not marker_type.is_integer() or marker_type < 0 for _, _, marker_type in markers):
        raise ValueError('Marker types must be non-negative integers')
    return map_start, markers


def make_pose(navigator, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = sin(yaw / 2)
    pose.pose.orientation.w = cos(yaw / 2)
    return pose


def call_service(navigator, client, request):
    future = client.call_async(request)
    rclpy.spin_until_future_complete(navigator, future, timeout_sec=10.0)
    if not future.done():
        raise RuntimeError(f'Timed out calling {client.srv_name}')
    return future.result()


def load_map(navigator, path):
    state_client = navigator.create_client(GetState, 'map_server/get_state')
    deadline = monotonic() + 30.0
    while rclpy.ok() and monotonic() < deadline:
        if state_client.wait_for_service(timeout_sec=1.0):
            state = call_service(navigator, state_client, GetState.Request())
            if state.current_state.id == State.PRIMARY_STATE_ACTIVE:
                break
        rclpy.spin_once(navigator, timeout_sec=0.2)
    else:
        raise RuntimeError('The Nav2 map server did not become active.')

    map_client = navigator.create_client(LoadMap, 'map_server/load_map')
    if not map_client.wait_for_service(timeout_sec=5.0):
        raise RuntimeError('The Nav2 load-map service is unavailable.')
    request = LoadMap.Request(map_url=str(path))
    response = call_service(navigator, map_client, request)
    if response.result != LoadMap.Response.RESULT_SUCCESS:
        raise RuntimeError(f'Nav2 could not load {path} (result {response.result}).')


def navigate(navigator):
    for name in ('map_file', 'marker_file'):
        navigator.declare_parameter(name, '')
    navigator.declare_parameter('odom_matches_map', False)
    map_file = navigator.get_parameter('map_file').value
    marker_file = navigator.get_parameter('marker_file').value
    if not map_file or not marker_file:
        raise ValueError('Set both ROS parameters: map_file and marker_file')
    map_path = Path(map_file).expanduser().resolve()
    if not map_path.is_file():
        raise ValueError(f'Map YAML does not exist: {map_path}')
    start, markers = read_route(
        Path(marker_file).expanduser(), navigator.get_parameter('odom_matches_map').value)

    load_map(navigator, map_path)
    navigator.setInitialPose(make_pose(navigator, *start))
    navigator.waitUntilNav2Active()

    previous_x, previous_y, yaw = start
    for index, (x, y, marker_type) in enumerate(markers, start=1):
        navigator.info(f'Visiting marker {index}/{len(markers)} (type {int(marker_type)}) at ({x:.3f}, {y:.3f})')
        if (x, y) != (previous_x, previous_y):
            yaw = atan2(y - previous_y, x - previous_x)
        if not navigator.goToPose(make_pose(navigator, x, y, yaw)):
            raise RuntimeError(f'Nav2 rejected marker {index}')
        while not navigator.isTaskComplete():
            pass  # BasicNavigator spins while waiting for action feedback and the result.
        result = navigator.getResult()
        if result != TaskResult.SUCCEEDED:
            raise RuntimeError(f'Navigation to marker {index} (type {int(marker_type)}) ended with {result.name}')
        previous_x, previous_y = x, y
        navigator.info(f'Reached marker {index}/{len(markers)}')
    navigator.info('Reached all markers in file order')


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    navigator = BasicNavigator(node_name='navigate_markers')
    try:
        navigate(navigator)
        return 0
    except (KeyboardInterrupt, ExternalShutdownException):
        if rclpy.ok() and navigator.goal_handle is not None:
            navigator.cancelTask()
        return 130
    except (OSError, ValueError, csv.Error, RuntimeError) as exc:
        navigator.error(str(exc))
        return 1
    finally:
        navigator.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
