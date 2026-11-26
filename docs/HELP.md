# Help and Mac settings

## Login details

On a fresh copy, the Ubuntu username is **student** and the password is **comp3431**, all lower case. Use your new password if you have changed it. Click inside the Ubuntu window before typing. This is separate from your Mac login.

## A Mac command file will not open

To start the VM, use **UTM → File → Open** and select **vm/COMP3431-Mac-ARM.utm**.

For the backup command, open Mac Terminal using **Command–Space → Terminal**. Type `zsh` followed by a space, drag **backup.command** from Finder into Terminal, then press **Return**. You can use the same method with **start.command**. No Mac security setting needs to be disabled.

## “course: command not found”

Open Terminal **inside Ubuntu**, not on the Mac. If needed, open **COMP3431 Terminal** from Ubuntu's applications list. The course software is installed inside the VM.

## The robot does not move

It starts stationary. Wait for **Ready**, then run `course wall-follow` or `course teleop`. Do not start a second simulator in another terminal. Use `course stop` before switching exercises.

## A simulation will not start

Read the error and log location printed in the Ubuntu terminal. Run `course stop`, then try `course start` once more. If it fails again, send the teaching team the error and the named log folder.

`course doctor --verbose` prints installation diagnostics. While a simulation is running, `course doctor --live --verbose` also checks real sensor data and transforms. The latest report is saved inside Ubuntu as **~/COMP3431/logs/doctor-latest.json**. Logs are not included by **backup.command**; keep or copy the requested diagnostic report separately for support.

## Saved VM settings

The package already saves the following settings. You normally do not need to edit them:

- Apple Silicon ARM64 with hardware virtualisation.
- **4 CPU cores**, **6144 MB memory** and a **64 GB virtual disk**.
- **Shared** networking for local simulation.
- Display card **virtio-ramfb**, **Retina mode off**, automatic display resizing on.
- Clipboard sharing on, with Ubuntu using the **Xorg** desktop session.

On each Mac, check **UTM → Settings → Display → Renderer Backend: Default**. This app-wide preference is not stored in the VM. Do not enable GPU acceleration for this course image. The supported display settings were checked with the simulator's laser and camera data.

If your Mac has only 8 GB memory, ask the teaching team for help. The supplied 6 GB VM allocation and a reduced 4 GB allocation have not been validated on an 8 GB Mac. Do not assign all your Mac's memory or CPU cores to the VM.

## Small desktop, black window or slow simulation

Resize the UTM window; Ubuntu should adjust its desktop. Keep Retina mode off and use a modest resolution such as **1280 × 800**. Ubuntu's **Settings → Displays** lets you select a resolution.

If you changed graphics settings, shut down Ubuntu, restore the settings above and start the VM again. A full VM shutdown is needed when changing its display hardware. Avoid force-stopping a working VM.

Simulation speed varies and can be substantially slower than real time. Use the default `course start` workflow, close other heavy apps, and keep enough free memory and disk space on the Mac. The additional Gazebo 3D window is optional and can be opened with `course start --gui`. The camera-off mapping mode is available for exercises that do not need vision; its speed benefit is not established.

UTM documents its [display and Retina settings](https://docs.getutm.app/settings-qemu/devices/display/).

## Mouse or keyboard captured by UTM

Press **Command–Option** to release input capture. Click inside the Ubuntu window to use its apps again. Ubuntu uses **Ctrl** for many shortcuts where Mac apps use **Command**.

## Backup fails

Keep the VM running, wait for Ubuntu to finish booting, and try **backup.command** again. Check the Mac has free disk space. If you denied Terminal permission to control UTM, review **System Settings → Privacy & Security → Automation** on the Mac and allow Terminal to control UTM for this operation. No network share or SSH setup is required.

If it still fails, retain the error and tell the teaching team. A file ending in **.partial** is not a completed backup; wait for the **Saved:** message. Do not delete the VM while trying to recover work.

## What has been tested

Login and the documented password, building all 14 course packages, ROS messaging, maze sensors, mapping, wall following, vision data processing, a short navigation goal and copying work to the Mac passed on an **M5 Pro, 48 GB, macOS 26.6.2**, using **UTM 4.7.5**.

Other Mac hardware, first-time installation on a second Mac, optional shared folders, physical robots and lab networking still need testing. The software is configured for simulation on this Mac. Follow the teaching team's instructions for physical-robot sessions. Software checks do not establish the correctness of assessed student solutions.

## Ask for help

Contact the teaching team through the course's usual help channel. Include your Mac chip, memory and macOS version, the UTM version, the command or step that failed, and the full error text. For a simulation error, also include the log folder printed by the command.

## Updates and removal

Back up work before updating Ubuntu or course packages, and follow the teaching team's update instructions. Do not change Ubuntu or ROS distributions to troubleshoot an exercise.

To remove the setup, back up your work, shut down Ubuntu and wait for **Stopped** in UTM. You can then remove the VM and its folder. Keep your backup archives if you still need the code and maps.
