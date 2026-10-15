import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    sumo = os.path.join(get_package_share_directory("sumo_gazebo"), "launch", "sumo.launch.py")
    return LaunchDescription([
        DeclareLaunchArgument("team", default_value="1", description="Your team number (1-7)"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(sumo),
            launch_arguments={"mode": "practice", "teams": LaunchConfiguration("team")}.items(),
        ),
    ])
