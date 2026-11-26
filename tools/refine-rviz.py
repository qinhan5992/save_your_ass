from pathlib import Path
from copy import deepcopy
import yaml
root=Path.home()/'COMP3431'
p=root/'config/course.rviz';data=yaml.safe_load(p.read_text());v=data['Visualization Manager']
v['Displays']=[d for d in v['Displays'] if d.get('Class') in ('rviz_default_plugins/Grid','rviz_default_plugins/Map','rviz_default_plugins/LaserScan','rviz_default_plugins/RobotModel')]
for d in v['Displays']:
 if d.get('Class')=='rviz_default_plugins/RobotModel':d['Name']='Robot'
v['Displays'].append({'Class':'rviz_default_plugins/MarkerArray','Name':'Course markers','Enabled':True,'Value':True,'Namespaces':{},'Topic':{'Value':'/visualization_marker_array','Depth':10,'Reliability Policy':'Reliable','Durability Policy':'Volatile','History Policy':'Keep Last'}})
v['Global Options']['Frame Rate']=10
data['Panels']=[p for p in data.get('Panels',[]) if p.get('Class')=='rviz_common/Displays']
for panel in data['Panels']:
 panel['Help Height']=40
 panel['Tree Height']=480
for name in ('course.rviz','navigation.rviz'):
 q=root/'config'/name
 d=data if name=='course.rviz' else yaml.safe_load(q.read_text())
 if name=='navigation.rviz':
  d=deepcopy(data)
  d['Panels'].append({'Class':'nav2_rviz_plugins/Navigation 2','Name':'Navigation 2'})
  manager=d['Visualization Manager']
  manager['Tools']=[t for t in manager['Tools'] if t.get('Class')!='rviz_default_plugins/SetGoal']
  manager['Tools'].append({'Class':'nav2_rviz_plugins/GoalTool'})
  for name_,topic,colour in (('Global path','/plan','0; 200; 255'),('Local path','/local_plan','255; 180; 0')):
   manager['Displays'].append({'Class':'rviz_default_plugins/Path','Name':name_,'Enabled':True,'Value':True,'Color':colour,'Alpha':1,'Line Style':'Lines','Line Width':0.03,'Topic':{'Value':topic,'Depth':5,'Reliability Policy':'Reliable','Durability Policy':'Volatile','History Policy':'Keep Last'}})
 d.setdefault('Window Geometry',{}).update({'Width':1000,'Height':620,'X':30,'Y':30})
 d['Window Geometry'].pop('QMainWindow State',None)
 q.write_text(yaml.safe_dump(d,sort_keys=False))
print('RViz: focused course displays, correct marker array topic, 1000x620 window.')
