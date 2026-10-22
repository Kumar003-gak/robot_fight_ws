import math
import os

import xacro
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction,
                            SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ARM_JOINTS = ["left_shoulder", "left_elbow", "right_shoulder", "right_elbow"]
WORLDS = {
    "practice": {"file": "practice_ring.sdf", "name": "sumo_practice", "radius": 2.0, "height": 0.3},
    "match": {"file": "sumo_arena.sdf", "name": "sumo_arena", "radius": 2.5, "height": 0.4},
}


def setup(context: LaunchContext) -> list:
    desc_share = get_package_share_directory("sumo_description")
    sim_share = get_package_share_directory("sumo_gazebo")
    with open(os.path.join(desc_share, "config", "teams.yaml")) as f:
        team_cfg = yaml.safe_load(f)["teams"]

    mode = LaunchConfiguration("mode").perform(context)
    world = WORLDS[mode]
    teams = [int(t) for t in LaunchConfiguration("teams").perform(context).split(",") if t.strip()]
    if any(t not in team_cfg for t in teams) or len(set(teams)) != len(teams):
        raise RuntimeError(f"teams must be different numbers from {sorted(team_cfg)}, got {teams}")
    if mode == "match" and len(teams) != 2:
        raise RuntimeError(f"a sumo match needs exactly 2 teams, got {teams}")
    if mode == "practice" and len(teams) != 1:
        raise RuntimeError(f"practice needs exactly 1 team, got {teams}")

    spawn_z = world["height"] + 0.12
    starts = [(-1.0, 0.0, 0.0)] if mode == "practice" else [(-1.2, 0.0, 0.0), (1.2, 0.0, math.pi)]
    robot_xacro = os.path.join(desc_share, "urdf", "sumo_bot.sdf.xacro")

    partition = f"ztr_team{teams[0]}" if mode == "practice" else "ztr_bigscreen"
    actions = [SetEnvironmentVariable("IGN_PARTITION", partition), IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": "-r " + os.path.join(sim_share, "worlds", world["file"])}.items(),
    )]

    bridge_args = [
        "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
        f"/world/{world['name']}/pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
    ]
    bridge_remaps = [(f"/world/{world['name']}/pose/info", "/arena/poses")]
    names = []
    for n, (x, y, yaw) in zip(teams, starts):
        name = f"team{n}"
        names.append(name)
        sdf = xacro.process_file(robot_xacro, mappings={
            "name": name, "color": team_cfg[n]["color"]}).toxml()
        actions.append(Node(
            package="ros_gz_sim", executable="create", output="screen",
            arguments=["-world", world["name"], "-name", name, "-string", sdf,
                       "-x", str(x), "-y", str(y), "-z", str(spawn_z), "-Y", str(yaw)],
        ))
        actions.append(Node(
            package="sumo_gazebo", executable="cmd_vel_guard.py", namespace=name,
            name="cmd_vel_guard", output="screen",
        ))
        bridge_args.append(f"/model/{name}/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist")
        bridge_remaps.append((f"/model/{name}/cmd_vel", f"/{name}/cmd_vel_safe"))
        for topic in [f"arm/{j}" for j in ARM_JOINTS] + ["face"]:
            bridge_args.append(f"/model/{name}/{topic}@std_msgs/msg/Float64]ignition.msgs.Double")
            bridge_remaps.append((f"/model/{name}/{topic}", f"/{name}/{topic}"))

    actions.append(Node(
        package="ros_gz_bridge", executable="parameter_bridge", name="sumo_bridge",
        output="screen", arguments=bridge_args, remappings=bridge_remaps,
    ))
    actions.append(Node(
        package="sumo_gazebo", executable="referee.py", name="referee", output="screen",
        parameters=[{
            "mode": mode,
            "fighters": names + (["dummy"] if mode == "practice" else []),
            "radius": world["radius"],
            "platform_height": world["height"],
            "time_limit_s": float(LaunchConfiguration("time_limit").perform(context)),
        }],
    ))
    return actions


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument("mode", default_value="practice", description="practice or match"),
        DeclareLaunchArgument("teams", default_value="1", description="Team numbers, e.g. 2,5"),
        DeclareLaunchArgument("time_limit", default_value="90.0", description="Match length, s"),
        OpaqueFunction(function=setup),
    ])
