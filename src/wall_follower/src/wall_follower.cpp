// Released under GPLv3: https://www.gnu.org/licenses/gpl-3.0.html
// Author: Claude Sammut
// Last Modified: 2024.10.14

// Use this code as the basis for a wall follower

#include "wall_follower/wall_follower.hpp"

#include <memory>


using namespace std::chrono_literals;

WallFollower::WallFollower()
: Node("wall_follower_node")
{
	/************************************************************
	** Initialise variables
	************************************************************/
	for (int i = 0; i < 12; i++)
		scan_data_[i] = 0.0;

	robot_pose_ = 0.0;
	near_start = false;

	/************************************************************
	** Initialise ROS publishers and subscribers
	************************************************************/
	auto qos = rclcpp::QoS(rclcpp::KeepLast(10));

	// Initialise publishers
	cmd_vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", qos);

	auto run_qos = rclcpp::QoS(1).transient_local();
	start_pose_pub_ = create_publisher<nav_msgs::msg::Odometry>("wall_follow_start", run_qos);
	finished_pub_ = create_publisher<std_msgs::msg::Empty>("wall_follow_finished", run_qos);

	// Initialise subscribers
	scan_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
		"scan", \
		rclcpp::SensorDataQoS(), \
		std::bind(
			&WallFollower::scan_callback, \
			this, \
			std::placeholders::_1));
	odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
		"odom", qos, std::bind(&WallFollower::odom_callback, this, std::placeholders::_1));

	/************************************************************
	** Initialise ROS timers
	************************************************************/
	update_timer_ = this->create_wall_timer(10ms, std::bind(&WallFollower::update_callback, this));

	RCLCPP_INFO(this->get_logger(), "Wall follower node has been initialised");
}

WallFollower::~WallFollower()
{
	RCLCPP_INFO(this->get_logger(), "Wall follower node has been terminated");
}

/********************************************************************************
** Callback functions for ROS subscribers
********************************************************************************/

#define START_RANGE	0.3
#define LEAVE_RANGE	1.0

void WallFollower::odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
	static bool start_moving = true;

	tf2::Quaternion q(
		msg->pose.pose.orientation.x,
		msg->pose.pose.orientation.y,
		msg->pose.pose.orientation.z,
		msg->pose.pose.orientation.w);
	tf2::Matrix3x3 m(q);
	double roll, pitch, yaw;
	m.getRPY(roll, pitch, yaw);

	robot_pose_ = yaw;

	current_y_ =  msg->pose.pose.position.y;
	current_x_ =  msg->pose.pose.position.x;
	if (!have_start_pose_)
	{
		start_x = current_x_;
		start_y = current_y_;
		start_pose_pub_->publish(*msg);
		have_start_pose_ = true;
	}
	else if (start_moving)
	{
		if (fabs(current_x_ - start_x) > LEAVE_RANGE || fabs(current_y_ - start_y) > LEAVE_RANGE)
			start_moving = false;
	}
	else if (fabs(current_x_ - start_x) < START_RANGE && fabs(current_y_ - start_y) < START_RANGE)
	{
		fprintf(stderr, "Near start!!\n");
		RCLCPP_INFO(this->get_logger(), "Startting the near start procedure");
		near_start = true;
	}
}

#define BEAM_WIDTH 15

void WallFollower::scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr msg)
{
	uint16_t scan_angle[12] = {0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330};

	double closest = msg->range_max;
	for (int angle = 360-BEAM_WIDTH; angle < 360; angle++)
		if (msg->ranges.at(angle) > 0.1 && msg->ranges.at(angle) < closest)
			closest = msg->ranges.at(angle);
	for (int angle = 0; angle < BEAM_WIDTH; angle++)
		if (msg->ranges.at(angle) > 0.1 && msg->ranges.at(angle) < closest)
			closest = msg->ranges.at(angle);
	scan_data_[0] = closest;

	for (int i = 1; i < 12; i++)
	{
		closest = msg->range_max;
		for (int angle = scan_angle[i]-BEAM_WIDTH; angle < scan_angle[i]+BEAM_WIDTH; angle++)
			if (msg->ranges.at(angle) >0.1 && msg->ranges.at(angle) < closest)
				closest = msg->ranges.at(angle);
		scan_data_[i] = closest;
	}
}

#define W 0.8
#define S (W < 1.0 ? W : 1.0)

void WallFollower::update_cmd_vel(double linear, double angular)
{
	geometry_msgs::msg::Twist cmd_vel;
	cmd_vel.linear.x = linear;
	cmd_vel.angular.z = angular;

	cmd_vel_pub_->publish(cmd_vel);
}

/********************************************************************************
** Update functions
********************************************************************************/

bool pl_near;

double STOP_TOLERANCE = 0.1;
double ANGULAR_DIRECTION_TOLERANCE = 0.25;

void WallFollower::update_callback()
{
	if (!have_start_pose_)
		return;

	if (near_start) {

		// get the distance from the current coordinates to the destination
		double diff_x = start_x - current_x_;
		double diff_y = start_y - current_y_;
		double dist = std::hypot(diff_x, diff_y);

		// close enough to the start so stop
		if (dist < STOP_TOLERANCE)
		{
			RCLCPP_INFO(this->get_logger(), "near start procedure complete");
			update_cmd_vel(0.0, 0.0);
			finished_pub_->publish(std_msgs::msg::Empty{});
			finished_pub_->wait_for_all_acked(500ms);
			rclcpp::shutdown();
			return;
		}

		// angle to start coordinates
		double target_yaw = std::atan2(diff_y, diff_x);
		double yaw_error = target_yaw - robot_pose_;

		// Normalize yaw_error to [-PI, PI]
		while (yaw_error > M_PI)  yaw_error -= 2.0 * M_PI;
		while (yaw_error < -M_PI) yaw_error += 2.0 * M_PI;

		// if not pointing towards the start then rotate otherwise drive towards start
		double ang_speed = 0.0;
		if (std::fabs(yaw_error) > ANGULAR_DIRECTION_TOLERANCE)
		{
			if (yaw_error > 0) {
				ang_speed = 0.5;
			}
			else {
				ang_speed = -0.5;
			}

			update_cmd_vel(0.0, ang_speed);
		}
		else
		{
			// drive towards start
			ang_speed = 0.4 * yaw_error;
			update_cmd_vel(0.08, ang_speed);
		}
	}
	else if (scan_data_[LEFT_FRONT] > 0.648) update_cmd_vel(0.1, 0.8);
	else if (scan_data_[FRONT] < 0.504) update_cmd_vel(0.0, -0.8);
	else if (scan_data_[FRONT_LEFT] < 0.432) update_cmd_vel(0.12, -0.6);
	else if (scan_data_[FRONT_RIGHT] < 0.432) update_cmd_vel(0.12, 0.6);
	else if (scan_data_[LEFT_FRONT] > 0.432) update_cmd_vel(0.12, 0.6);
	else update_cmd_vel(0.16, 0.0);
}



/*******************************************************************************
** Main
*******************************************************************************/
int main(int argc, char ** argv)
{
	rclcpp::init(argc, argv);
	rclcpp::spin(std::make_shared<WallFollower>());
	rclcpp::shutdown();

	return 0;
}
