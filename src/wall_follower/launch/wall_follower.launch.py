from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('marker_file', default_value='marker_route.csv'),
        Node(package='wall_follower', executable='wall_follower', name='wall_follower',
             parameters=[{'use_sim_time': use_sim_time}]),
        Node(package='wall_follower', executable='see_marker.py', name='see_marker',
             parameters=[{'use_sim_time': use_sim_time}],
             remappings=[('/camera/image_raw', '/camera/rgb/image_raw')]),
        Node(package='wall_follower', executable='point_transformer.py', name='point_transformer',
             parameters=[{'use_sim_time': use_sim_time,
                          'marker_file': LaunchConfiguration('marker_file')}]),
    ])
