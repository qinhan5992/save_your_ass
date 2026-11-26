#!/usr/bin/env python3
"""Check the stationary starting scene against broad expected maze clearances."""
import json,math,time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
rclpy.init();n=Node('comp3431_start_scene_check');messages=[]
s=n.create_subscription(LaserScan,'/scan',messages.append,qos_profile_sensor_data)
end=time.monotonic()+15
while len(messages)<3 and time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.1)
if not messages:raise SystemExit('FAIL: no scan')
m=messages[-1];v=[x for x in m.ranges if math.isfinite(x)]
front=min([x for x in list(m.ranges[:15])+list(m.ranges[-15:]) if math.isfinite(x)],default=0)
r={'beams':len(m.ranges),'minimum':min(v,default=0),'maximum':max(v,default=0),'front':front}
r['passed']=r['beams']==360 and .25<r['minimum']<.65 and 2.<r['maximum']<3.5 and 1.4<front<2.2
print(json.dumps(r,indent=2));n.destroy_node();rclpy.shutdown();raise SystemExit(0 if r['passed'] else 1)
