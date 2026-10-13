#!/usr/bin/env python3
import time

import rclpy
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64, String

GUARD = (-0.4, -1.8)
PUNCH = (-0.4, -1.8)  # TODO 3
ARMS_UP = (-2.8, 0.0)


class RobotController(Node):
    def __init__(self) -> None:
        super().__init__("robot_controller")
        self.max_speed = self.declare_parameter(
            "max_speed", 1.0, ParameterDescriptor(description="Forward speed, m/s")).value
        self.turn_speed = self.declare_parameter(
            "turn_speed", 2.5, ParameterDescriptor(description="Turn speed, rad/s")).value
        self.punch_time = self.declare_parameter(
            "punch_time_s", 0.4, ParameterDescriptor(description="How long a punch lasts, s")).value
        self.timeout = self.declare_parameter(
            "timeout_s", 0.6,
            ParameterDescriptor(description="Stop if no key for this long, s")).value

        self.cmd_pub = self.create_publisher(Twist, "cmd_vel", 10)
        self.arm_pubs = {
            joint: self.create_publisher(Float64, f"arm/{joint}", 10)
            for joint in ["left_shoulder", "left_elbow", "right_shoulder", "right_elbow"]
        }
        self.create_subscription(String, "robot_command", self.on_command, 10)

        self.command = "stop"
        self.command_time = 0.0
        self.left_punch_until = 0.0
        self.right_punch_until = 0.0
        self.arms_up_until = 0.0
        self.create_timer(0.05, self.update)
        self.get_logger().info("robot controller ready, waiting for commands")

    def on_command(self, msg: String) -> None:
        now = time.monotonic()
        self.command = msg.data
        self.command_time = now
        if msg.data == "punch_left":
            self.left_punch_until = now + self.punch_time
        # TODO 4
        elif msg.data == "arms_up":
            self.arms_up_until = now + 1.0

    def drive_for(self, command: str) -> Twist:
        twist = Twist()
        if command == "forward":
            twist.linear.x = self.max_speed
        # TODO 5
        return twist

    def arm_pose(self, punch_until: float, now: float) -> tuple[float, float]:
        if now < punch_until:
            return PUNCH
        if now < self.arms_up_until:
            return ARMS_UP
        return GUARD

    def update(self) -> None:
        now = time.monotonic()
        if now - self.command_time < self.timeout:
            self.cmd_pub.publish(self.drive_for(self.command))
        else:
            self.cmd_pub.publish(Twist())

        left = self.arm_pose(self.left_punch_until, now)
        right = self.arm_pose(self.right_punch_until, now)
        self.arm_pubs["left_shoulder"].publish(Float64(data=left[0]))
        self.arm_pubs["left_elbow"].publish(Float64(data=left[1]))
        # TODO 6


def main() -> None:
    rclpy.init()
    node = RobotController()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
