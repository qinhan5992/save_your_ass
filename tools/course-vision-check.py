#!/usr/bin/env python3
"""GUEST: exercise supplied segmentation on a real frame and a known image."""
import pathlib, importlib.util, cv2, numpy as np, json, sys
p=pathlib.Path.home()/'COMP3431'
f=p/'src/wall_follower/scripts/see_marker.py'
spec=importlib.util.spec_from_file_location('course_vision',f)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
img=cv2.imread(str(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else p/'logs/final-vision-camera.png'))
assert img is not None
h=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
r={'simulated_frame':{c:v.segment(img.copy(),h,c) for c in v.colours}}
hsv=np.zeros((480,640,3),np.uint8);hsv[:,:,2]=255
hsv[100:140,300:340]=[155,220,220];hsv[140:180,300:340]=[30,220,220]
bgr=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
r['known_pink_yellow_image']={c:v.segment(bgr.copy(),hsv,c) for c in v.colours}
assert r['known_pink_yellow_image']['pink'] is not None
assert r['known_pink_yellow_image']['yellow'] is not None
cv2.imwrite(str(p/'logs/known-pink-yellow.png'),bgr)
from wall_follower.landmark import Landmark
m=Landmark(0,[]).make_half_marker(0)
r['landmark_metadata']={'frame':m.header.frame_id,'quaternion_w':m.pose.orientation.w}
assert m.header.frame_id=='map' and m.pose.orientation.w==1.
s=json.dumps(r,indent=2,default=lambda v:v.item())
print(s);(p/'logs/course-vision-example.json').write_text(s)
