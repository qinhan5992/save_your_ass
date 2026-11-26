from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    bridge = Node(
        package='ros_ign_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
                # Velocity command (ROS2 -> IGN)
                '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
                # Odometry (IGN -> ROS2)
                '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
                # TF (IGN -> ROS2)
                '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
                # Clock (IGN -> ROS2)
                '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
                # Joint states (IGN -> ROS2)
                '/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model',
                # Lidar (IGN -> ROS2)
                '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
                '/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
                # IMU (IGN -> ROS2)
                '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                # Camera (IGN -> ROS2)
                '/camera/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
                '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                ],
        remappings=[
            ("/camera/image_raw", "/camera/rgb/image_raw"),
            ("/camera/camera_info", "/camera/rgb/camera_info"),
        ],
        output='screen'
    )

    map_static_tf = Node(package='tf2_ros',
                        executable='static_transform_publisher',
                        name='static_transform_publisher',
                        output='log',
                        arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'map', 'odom'])

    return LaunchDescription([
        bridge,
        # SLAM or AMCL must be the sole publisher of map -> odom.
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
    ])
