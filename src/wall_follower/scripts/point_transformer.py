#!/usr/bin/env python3

# Released under GPLv3: https://www.gnu.org/licenses/gpl-3.0.html
# Author: Claude Sammut
# Last Modified: 2024.10.14

# ROS 2 program to subscribe to update a MarkerArray subscribing to 
# PointStamed topic, assuming it's published by a vision node.

from collections import deque
from math import atan2
from pathlib import Path
import signal
from time import monotonic

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from geometry_msgs.msg import PointStamped, PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Empty
import tf2_ros
import tf2_geometry_msgs
from visualization_msgs.msg import MarkerArray
import csv


import wall_follower.landmark
from wall_follower.landmark import max_markers, Landmark


def planar_pose(pose):
	q = pose.orientation
	yaw = atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y**2 + q.z**2))
	return pose.position.x, pose.position.y, yaw


class PointTransformer(Node):

	def __init__(self):
		super().__init__('point_transformer')
		self.tf_buffer = tf2_ros.Buffer()
		self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
		self.point_subscriber = self.create_subscription(PointStamped, '/marker_position', self.point_callback, 10)
		self.marker_publisher_ = self.create_publisher(MarkerArray, 'visualization_marker_array', 10)
		self.declare_parameter('marker_file', 'marker_route.csv')
		self.start_odom = None
		self.start_map = None
		self.finish_at = None
		self.saved_route = False
		run_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
		self.start_subscription = self.create_subscription(
			Odometry, 'wall_follow_start', self.start_callback, run_qos)
		self.finish_subscription = self.create_subscription(
			Empty, 'wall_follow_finished', self.finish_callback, run_qos)
		self.pending_points = deque(maxlen=60)
		self.transform_timer = self.create_timer(0.02, self.process_pending_points)

		self.marker_position = []
		self.marker_array = MarkerArray()			
		self.marker_array.markers = []

		for i in range(max_markers):
			self.marker_position.append(Landmark(i, self.marker_array.markers))


	def saveLandmarks(self):
		with open('landmarks.csv', 'w', newline='') as csvfile:
			lm_writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
			for lm in self.marker_position:
				if lm.top_marker is not None:
					lm_writer.writerow(lm.toRow())


	def start_callback(self, msg):
		self.start_odom = msg
		self.start_map = None
		self.finish_at = None
		self.saved_route = False
		self.pending_points.clear()
		for landmark in self.marker_position:
			landmark.recent_positions.clear()

	def finish_callback(self, _msg):
		# Give the last camera observations time for their TF to arrive.
		self.finish_at = monotonic() + 0.5

	def capture_map_start(self):
		pose = PoseStamped()
		pose.header = self.start_odom.header
		pose.pose = self.start_odom.pose.pose
		try:
			transform = self.tf_buffer.lookup_transform(
				'map', pose.header.frame_id, Time.from_msg(pose.header.stamp))
		except tf2_ros.TransformException:
			return

		self.start_map = planar_pose(
			tf2_geometry_msgs.do_transform_pose_stamped(pose, transform).pose)

	def save_route(self):
		if self.saved_route or self.start_odom is None:
			return
		rows = [lm.toRow() for lm in self.marker_position if lm.recent_positions]
		if self.start_map is None or len(rows) != 4:
			self.get_logger().error(
				f'Route export needs the initial map transform and four markers. '
				f'Map transform available: {self.start_map is not None}. Markers recorded: {len(rows)}.')
			return

		path = Path(self.get_parameter('marker_file').value).expanduser().resolve()
		map_start_path = path.with_suffix('.start-map.csv')
		start = planar_pose(self.start_odom.pose.pose)
		try:
			for output, records in ((map_start_path, [start, self.start_map]),
			                        (path, [start, *rows])):
				temp = output.with_suffix(output.suffix + '.tmp')
				with temp.open('w', newline='') as stream:
					csv.writer(stream).writerows(records)
				temp.replace(output)
		except OSError as exc:
			self.get_logger().error(f'Could not export marker route: {exc}')
			return

		self.saved_route = True
		self.get_logger().info(f'Saved marker route to {path} and map start to {map_start_path}')


	def point_callback(self, msg):
		self.pending_points.append((monotonic() + 0.5, msg))

	def process_pending_points(self):
		if self.start_odom is not None and self.start_map is None:
			self.capture_map_start()

		# Retry without blocking the executor that receives TF updates.
		for _ in range(len(self.pending_points)):
			deadline, msg = self.pending_points.popleft()
			try:
				transform = self.tf_buffer.lookup_transform(
					'map', msg.header.frame_id, Time.from_msg(msg.header.stamp))
			except tf2_ros.TransformException:
				if monotonic() < deadline:
					self.pending_points.append((deadline, msg))
				else:
					self.get_logger().warning(
						'No map transform at the image timestamp', throttle_duration_sec=5.0)
				continue

			which_marker = int(msg.point.z)
			msg.point.z = 0.0
			map_point = tf2_geometry_msgs.do_transform_point(msg, transform)
			self.marker_position[which_marker].update_position(map_point.point)
			self.marker_publisher_.publish(self.marker_array)

		if self.finish_at is not None and monotonic() >= self.finish_at:
			self.finish_at = None
			self.save_route()


def main(args=None):
	stopping = False

	def request_stop(_signum, _frame):
		# The course wrapper and ROS launch can both signal this process.
		nonlocal stopping
		stopping = True

	signal.signal(signal.SIGINT, request_stop)
	signal.signal(signal.SIGTERM, request_stop)
	rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
	node = PointTransformer()
	try:
		while not stopping and rclpy.ok():
			rclpy.spin_once(node, timeout_sec=0.1)
		node.save_route()
		node.saveLandmarks()
	finally:
		node.destroy_node()
		rclpy.try_shutdown()


if __name__ == '__main__':
	main()

