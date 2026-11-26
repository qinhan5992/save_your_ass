#!/usr/bin/env bash
# Source in Ubuntu, never in the macOS terminal.
export COMP3431_HOME="$HOME/COMP3431"
export ROS_DOMAIN_ID=73 ROS_LOCALHOST_ONLY=1 TURTLEBOT3_MODEL=waffle_pi
export IGN_PARTITION=comp3431-local-simulation IGN_IP=127.0.0.1
source /opt/ros/humble/setup.bash
if [ -f "$COMP3431_HOME/install/setup.bash" ]; then
    source "$COMP3431_HOME/install/setup.bash"
fi
