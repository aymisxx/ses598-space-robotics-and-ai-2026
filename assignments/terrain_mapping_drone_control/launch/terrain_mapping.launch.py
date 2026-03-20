#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    """Generate launch description for terrain mapping with camera bridge."""
    
    # Get the package share directory
    pkg_share = get_package_share_directory('terrain_mapping_drone_control')
    
    # Get paths
    model_path = os.path.join(pkg_share, 'models')
    
  # Get the package share directory
    pkg_share = get_package_share_directory('terrain_mapping_drone_control')
        
    # Set Gazebo model and resource paths
    gz_model_path = os.path.join(pkg_share, 'models')

    # # Set initial drone pose
    os.environ['PX4_GZ_MODEL_POSE'] = "0,0,0.1,0,0,0"
    
    # Add launch argument for PX4-Autopilot path
    px4_autopilot_path = LaunchConfiguration('px4_autopilot_path')
    
    # Launch PX4 SITL with x500_depth
    px4_sitl = ExecuteProcess(
        cmd=['make', 'px4_sitl', 'gz_x500_gimbal'],
        cwd=px4_autopilot_path,
        output='screen'
    )
    
    # Spawn the cylinder model
    spawn_cylinder = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', os.path.join(model_path, 'cylinder', 'model.sdf'),
            '-name', 'cylinder',
            '-x', '5',  # 5 meters in front of the drone
            '-y', '0',
            '-z', '0',  # Base at ground level since the cylinder's origin is at its center
            '-R', '0',
            '-P', '0',
            '-Y', '0'
        ],
        output='screen'
    )
    spawn_terrain = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', os.path.join(model_path, 'terrain', 'model.sdf'),
            '-name', 'terrain',
            '-x', '0',
            '-y', '0',
            '-z', '-1.5',  # 5 meters below ground level
            '-R', '0',  # Roll (90 degrees)
            '-P', '0',  # Pitch
            '-Y', '0'  # Yaw (90 degrees counterclockwise)
        ],
        output='screen'
    )

    
    # Wrap cylinder spawning in TimerAction
    delayed_cylinder = TimerAction(
        period=2.0,
        actions=[spawn_cylinder]
    )

    delayed_terrain = TimerAction(
        period=2.0,
        actions=[spawn_terrain]
    )

    # Bridge node for camera and odometry
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='bridge',
        parameters=[{
            'use_sim_time': True,
        }],
        arguments=[
            # Camera topics (one-way from Gazebo to ROS)
            '/camera@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            # PX4 odometry (one-way from Gazebo to ROS)
             # Clock and Odometry
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',
            '/model/x500_depth_mono_0/odometry_with_covariance@nav_msgs/msg/Odometry@gz.msgs.OdometryWithCovariance',
         ],
        remappings=[
            ('/camera', '/drone_camera'),
            ('/camera_info', '/drone_camera_info'),
            ('/model/x500_gimbal_0/odometry_with_covariance', '/fmu/out/vehicle_odometry'),
        ],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='True',
            description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument(
            'px4_autopilot_path',
            default_value=os.environ.get('HOME', '/home/' + os.environ.get('USER', 'user')) + '/PX4-Autopilot',
            description='Path to PX4-Autopilot directory'),
        px4_sitl,
        TimerAction(
            period=2.0,
            actions=[delayed_cylinder]
        ),
         TimerAction(
            period=2.0,
            actions=[delayed_terrain]
        ),
        TimerAction(
            period=3.0,
            actions=[bridge]
        )
    ])
