#!/usr/bin/env python3
import math
import time

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64, String
from tf2_msgs.msg import TFMessage

FACE_HAPPY = 0.0
FACE_ANGRY = -1.5708
TIP_LIMIT = math.radians(60.0)


def roll_pitch(q) -> tuple[float, float]:
    roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (q.w * q.y - q.z * q.x))))
    return roll, pitch


class Referee(Node):
    def __init__(self) -> None:
        super().__init__("referee")
        self.fighters: list[str] = list(self.declare_parameter(
            "fighters", ["team1", "team2"],
            ParameterDescriptor(description="Model names to watch")).value)
        self.mode = self.declare_parameter(
            "mode", "match", ParameterDescriptor(description="match or practice")).value
        self.radius = self.declare_parameter(
            "radius", 2.5, ParameterDescriptor(description="Platform radius, m")).value
        self.top = self.declare_parameter(
            "platform_height", 0.4, ParameterDescriptor(description="Platform top height, m")).value
        self.time_limit = self.declare_parameter(
            "time_limit_s", 90.0, ParameterDescriptor(description="Match length, s")).value

        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.state_pub = self.create_publisher(String, "/arena/state", latched)
        self.result_pub = self.create_publisher(String, "/arena/result", latched)
        self.face_pubs = {name: self.create_publisher(Float64, f"/{name}/face", 10)
                          for name in self.fighters if name.startswith("team")}
        self.create_subscription(TFMessage, "/arena/poses", self.on_poses, 10)

        self.poses: dict = {}
        self.state = "waiting"
        self.countdown_start = 0.0
        self.fight_start = 0.0
        self.create_timer(0.1, self.update)
        self.get_logger().info(f"{self.mode} referee watching {', '.join(self.fighters)}")

    def on_poses(self, msg: TFMessage) -> None:
        for tf in msg.transforms:
            if tf.child_frame_id in self.fighters:
                self.poses[tf.child_frame_id] = tf.transform

    def is_out(self, name: str) -> bool:
        t = self.poses[name]
        roll, pitch = roll_pitch(t.rotation)
        fell = t.translation.z < self.top - 0.15
        tipped = abs(roll) > TIP_LIMIT or abs(pitch) > TIP_LIMIT
        return fell or tipped

    def set_state(self, state: str) -> None:
        self.state = state
        self.state_pub.publish(String(data=state))

    def set_face(self, name: str, angle: float) -> None:
        if name in self.face_pubs:
            self.face_pubs[name].publish(Float64(data=angle))

    def announce(self, text: str) -> None:
        bar = "=" * (len(text) + 8)
        self.get_logger().info(f"\n{bar}\n    {text}\n{bar}")

    def finish(self, text: str, winner: str | None) -> None:
        self.announce(text)
        self.result_pub.publish(String(data=text))
        if winner:
            self.set_face(winner, FACE_HAPPY)
        self.set_state("finished")

    def update(self) -> None:
        if self.state == "finished":
            return
        if self.state == "waiting":
            if all(name in self.poses for name in self.fighters):
                if self.mode == "practice":
                    self.announce("PRACTICE: push the dummy off the ring!")
                    self.fight_start = time.monotonic()
                    self.set_state("fight")
                else:
                    self.announce(f"{self.fighters[0].upper()}  vs  {self.fighters[1].upper()}")
                    self.countdown_start = time.monotonic()
                    self.set_state("ready")
            return
        if self.state in ("ready", "3", "2", "1"):
            elapsed = time.monotonic() - self.countdown_start
            step = ["ready", "3", "2", "1", "fight"][min(4, int(elapsed / 1.5))]
            if step != self.state:
                if step == "fight":
                    self.announce("FIGHT!")
                    for name in self.fighters:
                        self.set_face(name, FACE_ANGRY)
                    self.fight_start = time.monotonic()
                else:
                    self.get_logger().info(step)
                self.set_state(step)
            return

        elapsed = time.monotonic() - self.fight_start
        out = [name for name in self.fighters if self.is_out(name)]
        if self.mode == "practice":
            if "dummy" in out:
                self.finish(f"Dummy pushed out in {elapsed:.1f} s! Restart to try again.", None)
            elif out:
                self.finish(f"{out[0]} fell off the ring. Restart to try again.", None)
            return
        if len(out) == len(self.fighters):
            self.finish("DRAW: both robots are out!", None)
        elif out:
            winner = next(name for name in self.fighters if name not in out)
            self.finish(f"{winner.upper()} WINS! ({', '.join(out)} out after {elapsed:.1f} s)", winner)
        elif elapsed > self.time_limit:
            dist = {n: math.hypot(self.poses[n].translation.x, self.poses[n].translation.y)
                    for n in self.fighters}
            winner = min(dist, key=dist.get)
            self.finish(f"TIME! {winner.upper()} WINS, closest to the centre.", winner)


def main() -> None:
    rclpy.init()
    node = Referee()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
