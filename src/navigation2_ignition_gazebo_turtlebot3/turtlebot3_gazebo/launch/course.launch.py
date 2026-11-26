"""COMP3431 local simulation: complete world, consistent TF and optional viewers."""
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context):
    value = lambda key: LaunchConfiguration(key).perform(context)
    profile, mode = value('profile'), value('mode')
    if profile not in ('standard', 'balanced', 'mapping') or mode not in ('mapping', 'vision', 'navigation'):
        raise ValueError('Unknown COMP3431 profile or exercise mode')
    if profile == 'mapping' and mode == 'vision':
        raise ValueError('Vision requires balanced or standard profile')
    root = Path.home() / 'COMP3431'
    assets = Path(share('turtlebot3_gazebo'))
    models = assets / 'models'
    tree = ET.parse(models / 'worlds/world_only.sdf')
    world = tree.getroot().find('world')
    for engine in world.findall('plugin/render_engine'):
        engine.text = value('render_engine')
    # Embed the robot and include the maze before starting physics; no spawn races.
    robot = ET.parse(models / 'turtlebot3_waffle_pi/model.sdf').getroot().find('model')
    robot.set('name', 'waffle_pi')
    pose = robot.find('pose')
    if pose is None:
        pose = ET.SubElement(robot, 'pose')
    pose.text = '-0.6 1.5 0.01 0 0 0'
    for link in robot.findall('link'):
        for sensor in list(link.findall('sensor')):
            if sensor.get('type') == 'camera':
                if profile == 'mapping':
                    link.remove(sensor)
                elif profile == 'balanced':
                    sensor.find('update_rate').text = '10'
                    sensor.find('camera/image/width').text = '320'
                    sensor.find('camera/image/height').text = '240'
    if profile != 'standard':
        for shadow in world.findall('.//cast_shadows'):
            shadow.text = 'false'
    world.append(robot)
    for uri, pose in [
        ('worlds/turtlebot3_maze', '0 0 0 0 0 0'),
        ('yellow_on_pink_marker', '-0.7 -1.65 0.05 0 0 0'),
        ('pink_on_green_marker', '0.2 -1.55 0.05 0 0 0'),
        ('pink_on_yellow_marker', '2.3 1.55 0.05 0 0 0'),
        ('blue_on_pink_marker', '-0.7 0.45 0.05 0 0 0'),
    ]:
        inc = ET.SubElement(world, 'include')
        ET.SubElement(inc, 'uri').text = 'model://' + uri
        ET.SubElement(inc, 'pose').text = pose
    dest = Path(tempfile.mkdtemp(prefix='comp3431-world-')) / 'maze.sdf'
    tree.write(dest, encoding='unicode', xml_declaration=True)
    sim = ['ign', 'gazebo', '-r', '-v', '2', '--render-engine', value('render_engine')]
    if value('gui') != 'true':
        sim += ['-s']
    sim.append(str(dest))
    def include(package, launch, **kwargs):
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(share(package)) / 'launch' / launch)),
                                        launch_arguments=kwargs.items())
    actions = [
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', str(models) + ':/opt/ros/humble/share'),
        ExecuteProcess(cmd=sim, output='screen', additional_env={'LIBGL_ALWAYS_SOFTWARE': '1', 'LP_NUM_THREADS': '1'}),
        include('turtlebot3_gazebo', 'ros_ign_bridge.launch.py', use_sim_time='true'),
        include('turtlebot3_gazebo', 'robot_state_publisher.launch.py', use_sim_time='true'),
    ]
    if mode in ('mapping', 'vision'):
        actions.append(include('turtlebot3_cartographer', 'cartographer.launch.py', use_sim_time='true', use_rviz='false'))
    else:
        if not Path(value('map')).is_file():
            raise ValueError('An existing map YAML is required for navigation')
        actions.append(include('nav2_bringup', 'bringup_launch.py', use_sim_time='true',
                               map=value('map'), use_composition='False',
                               params_file=str(Path(share('turtlebot3_navigation2')) / 'param/humble/waffle_pi.yaml')))
    if mode == 'vision':
        actions += [Node(package='wall_follower', executable='see_marker.py',
                         parameters=[{'use_sim_time': True}],
                         remappings=[('/camera/image_raw', '/camera/rgb/image_raw')], output='screen'),
                    Node(package='wall_follower', executable='point_transformer.py',
                         parameters=[{'use_sim_time': True}], output='screen')]
    if value('rviz') == 'true':
        config = root / 'config' / ('navigation.rviz' if mode == 'navigation' else 'course.rviz')
        actions.append(Node(package='rviz2', executable='rviz2', arguments=['-d', str(config)],
                            parameters=[{'use_sim_time': True}], additional_env={'LP_NUM_THREADS': '1'}, output='screen'))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='balanced'),
        DeclareLaunchArgument('mode', default_value='mapping'),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('map', default_value=''),
        DeclareLaunchArgument('render_engine', default_value='ogre2'),
        OpaqueFunction(function=launch_setup),
    ])
