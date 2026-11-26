# COMP3431 in Ubuntu

The course software is installed. Open **COMP3431 Terminal** from the applications list, or press **Ctrl–Alt–T**.

Run `course doctor`, then `course start` and wait for **Ready**. Use `course wall-follow` to move the robot and `course stop` to finish.

Your editable code is in **/home/student/COMP3431/src**. Open it with `code ~/COMP3431`. After saving changes, run `course stop` and `course build`.

Open [START-HERE.html](START-HERE.html) for the complete guide, or read [Course commands](docs/COURSE-COMMANDS.md) and [Help](docs/HELP.md). The guide is also on your Ubuntu desktop.

To back up your work, leave Ubuntu running and use **backup.command** in the **mac-arm-setup** folder on your Mac. Finish by choosing **Power Off** in Ubuntu and waiting for UTM to show **Stopped**.

Initial username: **student**. Initial password: **comp3431**. Use your new password if you have changed it.

## Nav2 marker navigation

The project runs in two stages. First, the TurtleBot3 Waffle Pi follows the walls while Cartographer builds a map and the camera detects four markers. Then the robot starts again from the same position and heading, loads the saved map, initializes localization with AMCL, and uses Nav2 to visit the markers in CSV order. To change the visit order for the demonstration, rearrange the four marker rows and keep the starting pose on the first row.

### Code changes

| File | Changes |
| --- | --- |
| [`wall_follower.cpp`](src/wall_follower/src/wall_follower.cpp) | Records and publishes the first `/odom` message, including position, orientation, and timestamp. The robot must leave the starting area before it can detect a return. On return, it uses odometry to approach the starting point slowly, stops, and publishes `wall_follow_finished`. The wall-following speed and distance thresholds were adjusted, and laser readings below 0.1 m are ignored. |
| [`wall_follower.hpp`](src/wall_follower/include/wall_follower/wall_follower.hpp) | Adds publishers for the start and finish events and fields for the current position and whether the starting pose has been recorded. |
| [`point_transformer.py`](src/wall_follower/scripts/point_transformer.py) | Subscribes to the start and finish events and uses the first odometry timestamp to compute the starting pose in the map frame. It looks up marker transforms at the image timestamps and queues observations for retry when the transforms are temporarily unavailable. After the finish event it waits 0.5 seconds for final observations, checks for the starting transform and four marker types, and writes both CSVs through temporary files. On shutdown it also attempts to save the route and writes the legacy `landmarks.csv`. |
| [`see_marker.py`](src/wall_follower/scripts/see_marker.py) | Copies the image timestamp into each marker message. Estimates range using a focal length of about 530.47 px for the 640 × 480 camera and a color patch height of 0.10 m. Filters out small color blobs. |
| [`landmark.py`](src/wall_follower/wall_follower/landmark.py) | Uses the median of the five latest observations for each marker type to reduce the effect of outliers. |
| [`navigate_markers.py`](src/wall_follower/scripts/navigate_markers.py) **(new)** | Validates the route and companion starting pose, asks the Nav2 map server to load the specified map, and sets the initial pose in the `map` frame. Once Nav2 is ready, it sends goals with `goToPose()` in file order, advances after each success, and reports the waypoint number and type on failure. |
| [`CMakeLists.txt`](src/wall_follower/CMakeLists.txt) and [`package.xml`](src/wall_follower/package.xml) | Install the navigation script and declare the `std_msgs`, `lifecycle_msgs`, `nav2_msgs`, and `nav2_simple_commander` dependencies. |
| [`wall_follower.launch.py`](src/wall_follower/launch/wall_follower.launch.py) | Adds a `marker_file` launch argument that sets the exporter output path. |
| [`startup.bash`](src/wall_follower/startup.bash) and the [package README](src/wall_follower/README) | The startup script uses the course vision and wall-following commands. The package README documents mapping, saving, replaying, and reordering the route. |
| [`course.launch.py`](src/navigation2_ignition_gazebo_turtlebot3/turtlebot3_gazebo/launch/course.launch.py) and [`turtlebot3_maze.launch.py`](src/navigation2_ignition_gazebo_turtlebot3/turtlebot3_gazebo/launch/turtlebot3_maze.launch.py) | Update the robot spawn pose and four marker positions. Gazebo sessions are isolated with `IGN_PARTITION`. The standalone maze launch also limits software rendering threads. |
| [Maze `model.sdf`](src/navigation2_ignition_gazebo_turtlebot3/turtlebot3_gazebo/models/worlds/turtlebot3_maze/model.sdf) | Makes the maze and wall segments static and adjusts their positions and dimensions so the scene can be reproduced during mapping and replay. |
| [Humble `waffle_pi.yaml`](src/turtlebot3/turtlebot3_navigation2/param/humble/waffle_pi.yaml) | Switches the local controller from DWB to Regulated Pure Pursuit with a 0.30 m lookahead, a 0.18 m/s target speed, rotation to heading, and collision checking. The progress checker requires at least 0.15 m of movement within 15 seconds. |

| Output | Purpose |
| --- | --- |
| [`maps/demo.yaml`](maps/demo.yaml) and [`maps/demo.pgm`](maps/demo.pgm) **(new)** | The map used in the replay logs. The YAML stores the resolution, origin, and image reference. The PGM stores the occupancy grid. |
| [`maps/demo2.yaml`](maps/demo2.yaml) and [`maps/demo2.pgm`](maps/demo2.pgm) **(new)** | A second saved map from the workspace. |
| [`marker_route.csv`](marker_route.csv) **(new)** | A CSV with no header. The first row is `start_x,start_y,start_heading` in the odometry frame. The next four rows are `marker_x,marker_y,marker_type` in the map frame. Coordinates are in meters and heading is in radians. |
| [`marker_route.start-map.csv`](marker_route.start-map.csv) **(new)** | The first row repeats the odometry start. The second gives the same pose in the `map` frame. The replay node verifies that the first rows match and uses the second row to initialize AMCL. |
| [`landmarks.csv`](landmarks.csv) | The legacy export, populated with four rows of marker coordinates and types. |

### Development and validation

1. **Mapping and export.** The wall follower publishes the timestamped starting pose and sends a finish event when it returns near the start and stops. The transformer uses mapping-time TF for the marker coordinates and AMCL starting pose. The route CSV retains the original odometry pose required by the assignment. For example, an odometry start near `(0, 0, 0)` corresponds to a map-frame start of about `(0.024, -0.013, -0.001)` in the saved files. The mapping log records `Saved marker route`.
2. **Sequential Nav2 replay.** The navigation node loads the YAML through `map_server/load_map`, initializes AMCL, and waits for each action result. Early DWB runs reported `No valid trajectories` and `Failed to make progress`. The final configuration uses Regulated Pure Pursuit and allows more time for progress during slow turns and short moves. The script sends each CSV coordinate as a goal and derives its yaw from the direction between consecutive waypoints. If a goal fails, inspect its position relative to the walls and costmap in RViz to determine whether it needs a nearby stopping point.
3. **Four-goal replay and reordered routes.** A recorded run using `maps/demo.yaml` reported four `Goal succeeded` results in the order `0 → 2 → 3 → 4`. The first two marker x coordinates in that log were about `-0.13` and `-0.01`, which differ from the corresponding positive values in the current CSV. This verifies the route used in that run. To verify the current CSV or a reordered route, copy both CSVs, reorder only rows 2–5 in the main CSV if desired, and replay from the original starting pose. Compare the `Visiting marker` and `Reached marker` messages.

### Run the demonstration

Build and start mapping from the workspace root. The exporter uses fixed default filenames, so back up any CSVs you want to keep. Choose an unused name for the new map.

```bash
cd ~/COMP3431
course build
source install/setup.bash
course start vision
course wall-follow
```

When the robot returns near the start and the log shows `Saved marker route`, save the map while the mapping session is still running. Then switch to navigation.

```bash
course save-map nav-demo
course stop
course start navigation --map maps/nav-demo.yaml
ros2 run wall_follower navigate_markers.py --ros-args \
  -p use_sim_time:=true \
  -p map_file:=maps/nav-demo.yaml \
  -p marker_file:=marker_route.csv
```

Make sure the robot in navigation mode starts at the same position and heading as during mapping. A successful replay prints four `Reached marker` messages followed by `Reached all markers in file order`. Keep the YAML, PGM, route CSV, and companion start-pose CSV from the same run together with the navigation node for submission.
