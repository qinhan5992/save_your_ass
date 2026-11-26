# Set up your Mac

This package runs the course software inside **Ubuntu**, a Linux desktop opened through the Mac app **UTM**. A virtual machine (VM) is the saved Ubuntu computer. Its software is already installed; you only need to install UTM and open it.

Steps 1–4 happen **on your Mac**. Steps 5–6 happen **inside the Ubuntu window**.

## 1. Check your Mac

Choose **Apple menu → About This Mac**. You need an **Apple M-series chip** (M1, M2, M3, M4, M5 or later). This package does not support Intel Macs.

We recommend **at least 16 GB memory**. Allow **50 GB free disk space** before downloading and extracting the package, with more space later for your work and backups. Internet access is needed to download the package. No programming tools need to be installed on your Mac.

Testing used an M5 Pro with 48 GB memory and macOS 26.6.2. Other Mac models still need testing. An 8 GB Mac has not been validated with these settings; ask the teaching team before installing on one.

## 2. Download and keep the folder in place

Download the UTM course package from the course website. It is several gigabytes, so let the download finish completely. In Finder, open **Downloads** and double-click the ZIP if it has not already been extracted.

You should see a folder called **mac-arm-setup**. In Finder, choose **Go → Home**, create a folder called **COMP3431**, and move the whole **mac-arm-setup** folder into it. Keep it here throughout the course. Avoid iCloud, OneDrive or other cloud-sync folders for a running VM.

Open **mac-arm-setup**. You should see **START-HERE.html**, **start.command**, **backup.command**, **installer** and **vm**. Do not try to run the VM from inside the ZIP.

## 3. Install UTM on your Mac

Open **installer**, then double-click **UTM-4.7.5.dmg**. In the window that opens, drag **UTM** onto **Applications**. Wait for the copy to finish, then eject the disk image using Finder. Open **UTM** from Applications once.

The included installer is the official UTM 4.7.5 release used for testing. If macOS asks whether you want to open the downloaded UTM app, follow its normal Open prompt. No App Store purchase is required. If UTM is already installed, open it and check its version using **UTM → About UTM**; ask the teaching team if you are unsure about a different version.

## 4. Open the course VM and check one Mac setting

In UTM, choose **File → Open**, then select **vm/COMP3431-Mac-ARM.utm** inside your **mac-arm-setup** folder. The VM should appear as **COMP3431 Mac ARM**. Use this prepared VM; you do not need to create a new VM or install Ubuntu yourself.

In the Mac menu bar, choose **UTM → Settings → Display** and leave **Renderer Backend** set to **Default**. This is a setting on your Mac. The VM already contains the tested processor, memory, networking and display settings; keep those settings as supplied.

Select **COMP3431 Mac ARM** and press **Play**. Wait for the Ubuntu login screen. Next time, you can double-click **start.command** or open the VM directly in UTM.

## 5. Log in to Ubuntu

Click inside the Ubuntu window. Select **student** and enter this initial password, all lower case:

```text
Username: student
Password: comp3431
```

This password also works for `sudo` inside Ubuntu. It is separate from your Mac password. When a terminal asks for a password, no characters appear while you type; type it and press **Enter**.

You can change your Ubuntu password by running `passwd` in an Ubuntu terminal and following the prompts. Remember your new password and use it for future logins.

## 6. Check your first simulation

Inside Ubuntu, open **COMP3431 Terminal** from the applications list, or press **Ctrl–Alt–T** to open Terminal. Use the Ubuntu terminal for all `course` commands. Your Mac's Terminal is a different app and does not have the course software.

Run these commands **one at a time**, waiting for each to finish:

```sh
course doctor
course start
```

The first should print **PASS**. The second starts the robot simulator and opens **RViz**, the window showing the robot, laser readings and map. Wait for **Ready** in the terminal. The robot starts stationary.

Start the wall follower:

```sh
course wall-follow
```

You should see the robot move and the map grow. Simulation can run slower than real time. To stop wall following, then close the simulation:

```sh
course stop-robot
course stop
```

You are ready for the course once these checks succeed. When finished for the day, use **Power Off** in Ubuntu and wait until UTM shows the VM as **Stopped**. Closing a window alone is not the same as shutting down Ubuntu.

Official help: [Install UTM on macOS](https://docs.getutm.app/installation/macos/).
