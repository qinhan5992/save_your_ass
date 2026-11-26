#!/usr/bin/env bash
# GUEST: finite, independent C++ publisher and Python subscriber processes.
set -eo pipefail
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=73 ROS_LOCALHOST_ONLY=1
T="$HOME/COMP3431"
mkdir -p "$T/logs"
timeout --signal=INT 14 ros2 run demo_nodes_cpp talker > "$T/logs/demo-talker.log" 2>&1 &
talker=$!
timeout --signal=INT 12 ros2 run demo_nodes_py listener > "$T/logs/demo-listener.log" 2>&1 &
listener=$!
wait "$listener" || test "$?" = 124
wait "$talker" || test "$?" = 124
cat "$T/logs/demo-talker.log" "$T/logs/demo-listener.log"
grep -q 'I heard:' "$T/logs/demo-listener.log"
