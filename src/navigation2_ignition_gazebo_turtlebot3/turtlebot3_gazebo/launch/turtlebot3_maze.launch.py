import os
from uuid import uuid4
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

TURTLEBOT3_MODEL = os.environ['TURTLEBOT3_MODEL']   # waffle

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_name = LaunchConfiguration('world_name', default='turtlebot3_world')

    launch_file_dir = os.path.join(get_package_share_directory('turtlebot3_gazebo'), 'launch')

    ign_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',value=[
        os.path.join("/opt/ros/humble", "share"),
        ":" +
        os.path.join(get_package_share_directory("turtlebot3_gazebo"), "models"),
        ":" +
        os.path.join(get_package_share_directory('turtlebot3_gazebo'), "models")])

    # Spawn robot
    ignition_spawn_entity = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-entity', TURTLEBOT3_MODEL,
                   '-name', TURTLEBOT3_MODEL,
                   '-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "turtlebot3_waffle_pi", "model.sdf"]),
                   '-allow_renaming', 'true',
                   '-x', '-0.6553677',
                   '-y', '1.143383',
                   '-z', '0.01'],
        )
    
    
    # Spawn world
    ignition_spawn_world = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "worlds", "turtlebot3_maze","model.sdf"]),
                   '-allow_renaming', 'false'],
        )
    
    spawn_marker1 = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "yellow_on_pink_marker","model.sdf"]),
            '-x', '-0.7453677',
            '-y', '-1.691617',
            '-z', '0.05' ]
    )

    spawn_marker2 = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "pink_on_green_marker","model.sdf"]),
            '-x', '0.0646323',
            '-y', '-1.601617',
            '-z', '0.05' ]
    )

    spawn_marker3 = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "pink_on_yellow_marker","model.sdf"]),
            '-x', '1.9546323',
            '-y', '1.188383',
            '-z', '0.05' ]
    )

    spawn_marker4 = Node(
        package='ros_ign_gazebo',
        executable='create',
        output='screen',
        arguments=['-file', PathJoinSubstitution([
                        get_package_share_directory('turtlebot3_gazebo'),
                        "models", "blue_on_pink_marker","model.sdf"]),
            '-x', '-0.7453677',
            '-y', '0.198383',
            '-z', '0.05' ]
    )

    world_only = os.path.join(get_package_share_directory('turtlebot3_gazebo'), "models", "worlds", "world_only.sdf")

    return LaunchDescription([
        SetEnvironmentVariable(
            name='IGN_PARTITION',
            value=f'comp3431-maze-{uuid4().hex}'),
        ign_resource_path,
        SetEnvironmentVariable(name='LIBGL_ALWAYS_SOFTWARE', value='1'),
        SetEnvironmentVariable(name='LP_NUM_THREADS', value='1'),
        ignition_spawn_entity,
        ignition_spawn_world,
        spawn_marker1,
        spawn_marker2,
        spawn_marker3,
        spawn_marker4,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(get_package_share_directory('ros_ign_gazebo'),
                              'launch', 'ign_gazebo.launch.py')]),
            launch_arguments=[('gz_args', [' -r -v 3 ' +
                              world_only
                             ])]),
                             
        DeclareLaunchArgument(
            'use_sim_time',
            default_value=use_sim_time,
            description='If true, use simulated clock'),

        DeclareLaunchArgument(
            'world_name',
            default_value=world_name,
            description='World name'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([launch_file_dir, '/ros_ign_bridge.launch.py']),
            launch_arguments={'use_sim_time': use_sim_time}.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([launch_file_dir, '/robot_state_publisher.launch.py']),
            launch_arguments={'use_sim_time': use_sim_time}.items(),
        ),
    ])
