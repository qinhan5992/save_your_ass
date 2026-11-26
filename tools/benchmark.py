#!/usr/bin/env python3
"""GUEST: bounded observation of real simulation messages; no motion commands."""
import collections, hashlib, json, math, os, pathlib, sys, time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan, Image
from nav_msgs.msg import Odometry, OccupancyGrid
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from tf2_ros import Buffer, TransformListener

duration=float(sys.argv[1]); label=sys.argv[2]
root=pathlib.Path.home()/'COMP3431'
rclpy.init()
n=Node('comp3431_test_probe', parameter_overrides=[Parameter('use_sim_time', value=True)])
buf=Buffer(); listener=TransformListener(buf,n)
counts=collections.Counter(); first={}; last={}; scan_hashes=set(); points=[]; commands=[]; errors=[]; image_result={}; map_result={}
def stamp(v): return v.sec+v.nanosec/1e9
def record(k,v):
 counts[k]+=1; first.setdefault(k,v); last[k]=v
def scan(m):
 finite=[x for x in m.ranges if math.isfinite(x)]
 v={'stamp':stamp(m.header.stamp),'frame':m.header.frame_id,'beams':len(m.ranges),'min':min(finite) if finite else None,'max':max(finite) if finite else None,'front':min([x for x in list(m.ranges[:15])+list(m.ranges[-15:]) if math.isfinite(x)],default=None)}
 record('scan',v); scan_hashes.add(hashlib.sha256(m.ranges.tobytes()).hexdigest())
def odom(m):
 p=m.pose.pose.position; q=m.pose.pose.orientation
 v={'stamp':stamp(m.header.stamp),'frame':m.header.frame_id,'child':m.child_frame_id,'x':p.x,'y':p.y,'yaw':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))}
 record('odom',v); points.append([p.x,p.y])
def cmd(m):
 record('cmd_vel',{'linear':m.linear.x,'angular':m.angular.z})
 if len(commands)<2000:commands.append({'wall':time.monotonic(),'linear':m.linear.x,'angular':m.angular.z,'front':last.get('scan',{}).get('front')})
def camera(m):
 record('camera',{'stamp':stamp(m.header.stamp),'frame':m.header.frame_id,'width':m.width,'height':m.height,'encoding':m.encoding})
 if image_result:return
 try:
  bgr=CvBridge().imgmsg_to_cv2(m,desired_encoding='bgr8')
  hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
  image_result.update({'opencv':cv2.__version__,'shape':list(bgr.shape),'mean_bgr':bgr.mean(axis=(0,1)).tolist(),'saturated_pixels':int(np.count_nonzero(hsv[:,:,1]>120))})
  cv2.imwrite(str(root/'logs'/f'{label}-camera.png'),bgr)
 except Exception as e:errors.append(str(e))
def grid(m):
 a=np.asarray(m.data); record('map',{'stamp':stamp(m.header.stamp),'width':m.info.width,'height':m.info.height,'frame':m.header.frame_id})
 map_result.update({'known':int(np.count_nonzero(a>=0)),'occupied':int(np.count_nonzero(a>50)),'free':int(np.count_nonzero(a==0)),'resolution':m.info.resolution,'origin':[m.info.origin.position.x,m.info.origin.position.y]})
subs=[n.create_subscription(Clock,'/clock',lambda m:record('clock',stamp(m.clock)),qos_profile_sensor_data),n.create_subscription(LaserScan,'/scan',scan,qos_profile_sensor_data),n.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data),n.create_subscription(Twist,'/cmd_vel',cmd,10),n.create_subscription(Image,'/camera/rgb/image_raw',camera,qos_profile_sensor_data),n.create_subscription(OccupancyGrid,'/map',grid,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))]
start=time.monotonic()
while time.monotonic()-start<duration:rclpy.spin_once(n,timeout_sec=0.1)
elapsed=time.monotonic()-start
transforms={}
for parent,child in [('map','odom'),('odom','base_footprint'),('base_footprint','base_link'),('base_link','base_scan'),('base_link','camera_link'),('base_link','camera_rgb_frame'),('map','base_link')]:
 try:
  t=buf.lookup_transform(parent,child,rclpy.time.Time()); p=t.transform.translation
  transforms[parent+' -> '+child]={'xyz':[p.x,p.y,p.z],'stamp':stamp(t.header.stamp)}
 except Exception as e: transforms[parent+' -> '+child]={'error':str(e)}
result={'label':label,'elapsed_wall_s':elapsed,'counts':dict(counts),'wall_hz':{k:v/elapsed for k,v in counts.items()},'first':first,'last':last,'unique_scans':len(scan_hashes),'odom_path_m':sum(math.dist(a,b) for a,b in zip(points,points[1:])),'command_samples':commands,'image_processing':image_result,'map':map_result,'transforms':transforms,'errors':errors}
if 'clock' in first:result['observed_real_time_factor']=(last['clock']-first['clock'])/elapsed
(root/'logs'/f'{label}.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='command_samples'},indent=2))
n.destroy_node();rclpy.shutdown()
