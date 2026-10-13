from setuptools import setup

package_name = "sumo_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Kumar003-gak",
    description="Zero to Robot sumo workshop: student nodes.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "keyboard_teleop = sumo_control.keyboard_teleop:main",
            "robot_controller = sumo_control.robot_controller:main",
        ],
    },
)
