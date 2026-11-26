# Working on the course

Start the VM with **start.command**, sign in to Ubuntu, and open **COMP3431 Terminal** inside Ubuntu. Run the commands below there, one line at a time.

## Start, move and stop

```sh
course start
course wall-follow
course stop-robot
course stop
```

These commands start the maze and mapping, start wall following, stop wall following, then close the simulation. Use them as needed. Run `course status` to check whether the simulation is running. Use `course reset` to restart the current exercise at the robot's initial pose; saved maps and source edits are retained.

For keyboard control, start the simulation and run `course teleop`. Follow the keys printed in the terminal, then press **Ctrl–C** to leave keyboard control.

## Edit and build your code

Your code is inside Ubuntu at **/home/student/COMP3431/src**. The wall-following and vision examples are in **src/wall_follower**. Open the workspace in the installed VS Code editor:

```sh
code ~/COMP3431
```

Save your edits, then stop the simulation and rebuild:

```sh
course stop
course build
```

Wait for the build to finish before running your code again. Open a fresh Ubuntu terminal after adding packages. Edit source files in **src**, not generated files in **build** or **install**.

The normal `ros2 run`, `ros2 topic` and `ros2 node` commands are available. For a messaging exercise, open two Ubuntu terminals. Run `ros2 run demo_nodes_cpp talker` in one and `ros2 run demo_nodes_py listener` in the other. Press **Ctrl–C** in each when finished.

## Camera and marker exercise

```sh
course stop
course start vision
course wall-follow
```

Vision mode selects the 640 × 480 camera resolution expected by the supplied code. It opens a camera window and runs the marker-processing example. Finish with `course stop`.

For mapping exercises that do not use the camera, `course start mapping --profile mapping` disables it. Stop the current simulation before switching modes. This option is not a guarantee of faster simulation.

## Save a map

While mapping is running, stop wall following and save your map:

```sh
course stop-robot
course save-map my-map
```

This creates **~/COMP3431/maps/my-map.yaml** and **~/COMP3431/maps/my-map.pgm** inside Ubuntu. Use a new name for each map you want to keep; existing maps are protected from overwrite.

## Navigate with a saved map

```sh
course stop
course start navigation --map ~/COMP3431/maps/my-map.yaml
```

In RViz, select **2D Pose Estimate**, then click and drag at the robot's current position and heading. Once the laser readings line up with the map, select **Nav2 Goal**, then click and drag at your destination. Choose a clear area of mapped floor.

Use RViz to cancel an active navigation goal. `course stop-robot` stops wall following; it does not cancel a Nav2 goal. `course stop` closes the whole simulation.

## Back up your work to your Mac

Save your files in Ubuntu and run `course stop`. **Leave Ubuntu and the VM running.** On your Mac, open **mac-arm-setup** in Finder and double-click **backup.command**.

If macOS asks whether Terminal can control UTM, allow that specific Automation permission to use the backup tool. Wait for **Saved:** and a Finder window showing the new backup. The first backup can take a few minutes.

Each backup is a new dated **.tar.gz** archive in **student-backups** beside the Mac launchers. It contains your Ubuntu **src**, **maps**, **tools** and **config** folders. It does not include arbitrary files elsewhere in Ubuntu. Check that the backup exists before shutting down. Keep another copy of important backups somewhere safe.

To recover work, keep the backup archive unchanged and ask the teaching team to help extract the needed files into your Ubuntu workspace. Rebuild with `course build` after restoring source code. Do not replace the whole VM just to recover one file.

## Finish your session

Run `course stop`, save and back up your work, then choose **Power Off** from Ubuntu's top-right system menu. Wait for UTM to show **Stopped** before moving or copying the VM folder.

Your work is stored inside **vm/COMP3431-Mac-ARM.utm**. Deleting that VM also deletes any work inside it that you have not backed up.
