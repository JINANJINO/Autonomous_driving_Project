from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():
    use_rviz_config = LaunchConfiguration("use_rviz_config", default="false")

    # env.py 라는 entry-point는 midterm_env/setup.py에 이미 등록되어 있음: env = midterm_env.env:main
    env_node = Node(
        package="midterm_env",
        executable="env",
        name="driving_env",
        output="screen",
    )

    planner_node = Node(
        package="auto_driving2",
        executable="planner",
        name="integrated_planner_rviz",
        output="screen",
    )

    # 기본 RViz (config 없으면 빈 RViz)
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
    )

    return LaunchDescription([
        env_node,
        planner_node,
        rviz_node,
    ])
