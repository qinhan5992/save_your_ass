#!/usr/bin/env python3
"""GUEST: preserve a SLAM pose or execute one short, checked Nav2 test goal."""
import collections, json, math, pathlib, sys, time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from tf2_ros import Buffer, TransformListener

root=pathlib.Path.home()/'COMP3431'
rclpy.init(); n=Node('comp3431_navigation_check',parameter_overrides=[Parameter('use_sim_time',value=True)])
buf=Buffer(); listener=TransformListener(buf,n)
def spin_until(test,seconds):
 end=time.monotonic()+seconds
 while not test() and time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.1)
 return test()
if sys.argv[1]=='prepare':
 latest=[]
 sub=n.create_subscription(OccupancyGrid,'/map',lambda m: latest.append(m),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
 if not spin_until(lambda:bool(latest) and buf.can_transform('map','base_footprint',rclpy.time.Time()),30):raise RuntimeError('No live map/robot transform')
 t=buf.lookup_transform('map','base_footprint',rclpy.time.Time()); p=t.transform.translation; q=t.transform.rotation; m=latest[-1]
 pose={'x':p.x,'y':p.y,'z':0.,'qx':q.x,'qy':q.y,'qz':q.z,'qw':q.w}
 grid=np.asarray(m.data,dtype=np.int16).reshape(m.info.height,m.info.width)
 clearance=cv2.distanceTransform(((grid>=0)&(grid<50)).astype(np.uint8),cv2.DIST_L2,5)*m.info.resolution
 ox=m.info.origin.position.x; oy=m.info.origin.position.y; res=m.info.resolution
 cx=int((p.x-ox)/res); cy=int((p.y-oy)/res)
 queue=collections.deque([(cy,cx,0)]); seen={(cy,cx)}; candidates=[]
 while queue:
  y,x,steps=queue.popleft()
  if not(0<=x<m.info.width and 0<=y<m.info.height):continue
  dist=math.hypot(ox+(x+.5)*res-p.x,oy+(y+.5)*res-p.y)
  if .45<=dist<=.7 and clearance[y,x]>=.25:candidates.append((abs(dist-.55)-.1*float(clearance[y,x]),y,x,steps))
  if steps>=40:continue
  for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
   yy,xx=y+dy,x+dx
   if (yy,xx) not in seen and 0<=xx<m.info.width and 0<=yy<m.info.height and clearance[yy,xx]>=.22:
    seen.add((yy,xx)); queue.append((yy,xx,steps+1))
 if not candidates:raise RuntimeError('No sufficiently clear reachable test goal within 0.7 m')
 _,y,x,steps=min(candidates); goal={'x':ox+(x+.5)*res,'y':oy+(y+.5)*res,'clearance_m':float(clearance[y,x]),'grid_path_steps':steps}
 result={'initial_pose':pose,'goal':goal}; (root/'maps/initial-and-goal.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
else:
 data=json.loads((root/'maps/initial-and-goal.json').read_text()); p=data['initial_pose']; g=data['goal']; states={}
 for name in ('map_server','amcl'):
  c=n.create_client(GetState,f'/{name}/get_state')
  if not c.wait_for_service(timeout_sec=60):raise RuntimeError(name+' lifecycle unavailable')
  end=time.monotonic()+90
  while time.monotonic()<end:
   f=c.call_async(GetState.Request()); spin_until(f.done,5)
   if f.done() and f.result():states[name]=f.result().current_state.label
   if states.get(name)=='active':break
  if states.get(name)!='active':raise RuntimeError(str(states))
 init=n.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
 msg=PoseWithCovarianceStamped(); msg.header.frame_id='map'; msg.pose.pose.position.x=p['x']; msg.pose.pose.position.y=p['y']
 for attr in 'xyzw':setattr(msg.pose.pose.orientation,attr,p['q'+attr])
 msg.pose.covariance[0]=.04;msg.pose.covariance[7]=.04;msg.pose.covariance[35]=.04
 for _ in range(5):
  msg.header.stamp=n.get_clock().now().to_msg();init.publish(msg)
  end=time.monotonic()+1
  while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.1)
 if not spin_until(lambda:buf.can_transform('map','base_footprint',rclpy.time.Time()),60):raise RuntimeError('AMCL did not supply map transform')
 for name in ('controller_server','planner_server','bt_navigator'):
  c=n.create_client(GetState,f'/{name}/get_state')
  if not c.wait_for_service(timeout_sec=60):raise RuntimeError(name+' lifecycle unavailable')
  end=time.monotonic()+90
  while time.monotonic()<end:
   f=c.call_async(GetState.Request());spin_until(f.done,5)
   if f.done() and f.result():states[name]=f.result().current_state.label
   if states.get(name)=='active':break
  if states.get(name)!='active':raise RuntimeError(str(states))
 print('ACTIVE_LIFECYCLE '+json.dumps(states),flush=True)
 client=ActionClient(n,NavigateToPose,'/navigate_to_pose')
 if not client.wait_for_server(timeout_sec=60):raise RuntimeError('Navigation action unavailable')
 goal=NavigateToPose.Goal();goal.pose=PoseStamped();goal.pose.header.frame_id='map';goal.pose.header.stamp=n.get_clock().now().to_msg();goal.pose.pose.position.x=g['x'];goal.pose.pose.position.y=g['y']
 for attr in 'xyzw':setattr(goal.pose.pose.orientation,attr,p['q'+attr])
 f=client.send_goal_async(goal);spin_until(f.done,15);handle=f.result()
 if not handle or not handle.accepted:raise RuntimeError('Goal rejected')
 print('GOAL_ACCEPTED '+json.dumps(g),flush=True); f=handle.get_result_async();start=time.monotonic()
 if not spin_until(f.done,300):
  cancel=handle.cancel_goal_async();spin_until(cancel.done,15);raise RuntimeError('Navigation timed out; goal cancelled')
 t=buf.lookup_transform('map','base_footprint',rclpy.time.Time()); v=t.transform.translation
 result={'states':states,'action_status':f.result().status,'elapsed_wall_s':time.monotonic()-start,'goal':g,'final_position':[v.x,v.y],'position_error_m':math.hypot(v.x-g['x'],v.y-g['y'])}
 (root/'logs/navigation-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 if result['action_status']!=4:raise RuntimeError('Nav2 goal did not succeed')
n.destroy_node();rclpy.shutdown()
