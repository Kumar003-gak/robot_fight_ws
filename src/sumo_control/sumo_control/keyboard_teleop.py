#!/usr/bin/env python3
import select
import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

KEY_BINDINGS: dict[str, str] = {
    "w": "forward",
    " ": "stop",
    # TODO 1
}

HELP = """
  SUMO ROBOT KEYBOARD
  -------------------
      w             q / e : punch left / right
    a s d           f     : punch with both arms
                    r     : arms up
  space : stop      Ctrl+C: quit
  Hold a key to keep moving.
"""


class KeyboardTeleop(Node):
    def __init__(self) -> None:
        super().__init__("keyboard_teleop")
        self.publisher = self.create_publisher(String, "robot_command", 10)

    def send(self, command: str) -> None:
        msg = String()
        # TODO 2


def read_key(timeout_s: float) -> str:
    ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    return sys.stdin.read(1) if ready else ""


def main() -> None:
    rclpy.init()
    node = KeyboardTeleop()
    old_settings = termios.tcgetattr(sys.stdin)
    print(HELP)
    try:
        tty.setraw(sys.stdin.fileno())
        while rclpy.ok():
            key = read_key(0.1).lower()
            if key == "\x03":
                break
            if key in KEY_BINDINGS:
                command = KEY_BINDINGS[key]
                node.send(command)
                print(f"\r  sent: {command:<12}", end="", flush=True)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
