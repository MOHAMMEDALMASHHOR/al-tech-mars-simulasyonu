import random

def generate_world():
    xml = '''<?xml version="1.0" ?>
<sdf version="1.5">
  <world name="martian_training_world">
    <!-- Scene Settings optimized for YOLO Training Contrast -->
    <scene>
      <ambient>0.7 0.7 0.7 1.0</ambient>
      <background>0.8 0.4 0.1 1.0</background>
      <shadows>1</shadows>
      <!-- Reduced fog to make bounding box labeling easier from the sky -->
      <fog>
        <color>0.8 0.4 0.1 1.0</color>
        <type>linear</type>
        <start>20</start>
        <end>300</end>
        <density>0.05</density>
      </fog>
    </scene>

    <gravity>0 0 -3.711</gravity>

    <!-- Sun: Balanced to avoid extreme shadows that confuse YOLO -->
    <light name='martian_sun' type='directional'>
      <cast_shadows>1</cast_shadows>
      <pose>0 0 50 0 0 0</pose>
      <diffuse>0.9 0.8 0.7 1</diffuse>
      <specular>0.5 0.5 0.5 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.3 0.3 -0.9</direction>
    </light>

    <!-- Martian Ground: Distinct Orange for YOLO differentiation -->
    <model name='martian_ground'>
      <static>1</static>
      <link name='link'>
        <collision name='collision'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>800 800</size>
            </plane>
          </geometry>
          <surface>
            <friction><ode><mu>100</mu><mu2>50</mu2></ode></friction>
          </surface>
        </collision>
        <visual name='visual'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>800 800</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.8 0.4 0.1 1</ambient>
            <diffuse>0.9 0.45 0.15 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
          </material>
        </visual>
      </link>
    </model>
'''
    # Generate 40 Water Ice spots (pure white)
    random.seed(1337) # reproducible
    for i in range(40):
        x = random.uniform(-150, 150)
        y = random.uniform(-150, 150)
        
        # Don't place right at 0,0 (base)
        if abs(x) < 5 and abs(y) < 5: continue
            
        rot_z = random.uniform(0, 3.14)
        
        ice = f'''
    <!-- Water Ice (White) -->
    <model name="water_ice_{i}">
      <static>true</static>
      <pose>{x:.2f} {y:.2f} 0.01 0 0 {rot_z:.2f}</pose>
      <link name="link">
        <visual name="v"><geometry><cylinder><radius>{random.uniform(1.5, 3.5):.2f}</radius><length>0.1</length></cylinder></geometry>
          <material><ambient>1.0 1.0 1.0 1</ambient><diffuse>1.0 1.0 1.0 1</diffuse><specular>0.8 0.8 0.8 1</specular></material>
        </visual>
        <visual name="v2"><pose>{random.uniform(0.5, 1.5):.2f} {random.uniform(0.5, 1.5):.2f} 0 0 0 0</pose><geometry><cylinder><radius>{random.uniform(1.0, 2.0):.2f}</radius><length>0.1</length></cylinder></geometry>
          <material><ambient>1.0 1.0 1.0 1</ambient><diffuse>1.0 1.0 1.0 1</diffuse><specular>0.8 0.8 0.8 1</specular></material>
        </visual>
        <collision name="c"><geometry><cylinder><radius>3.5</radius><length>0.1</length></cylinder></geometry></collision>
      </link>
    </model>
'''
        xml += ice

    # Generate 50 Regolith spots (dark brown)
    for i in range(50):
        x = random.uniform(-150, 150)
        y = random.uniform(-150, 150)
        
        if abs(x) < 5 and abs(y) < 5: continue
        
        rot_z = random.uniform(0, 3.14)
        
        spheres = ""
        num_spheres = random.randint(3, 8)
        max_r = 0.0
        for s in range(num_spheres):
            sx = random.uniform(-1.5, 1.5)
            sy = random.uniform(-1.5, 1.5)
            sr = random.uniform(0.2, 0.45)
            sz = sr / 2.0  # sit on ground
            max_r = max(max_r, sr+abs(sx)+abs(sy))
            spheres += f'''
        <visual name="v{s}"><pose>{sx:.2f} {sy:.2f} {sz:.2f} 0 0 0</pose><geometry><sphere><radius>{sr:.2f}</radius></sphere></geometry>
          <material><ambient>0.3 0.15 0.05 1</ambient><diffuse>0.35 0.18 0.08 1</diffuse></material>
        </visual>
        <collision name="c{s}"><pose>{sx:.2f} {sy:.2f} {sz:.2f} 0 0 0</pose><geometry><sphere><radius>{sr:.2f}</radius></sphere></geometry></collision>
'''
        
        reg = f'''
    <!-- Regolith (Dark Brown) -->
    <model name="regolith_field_{i}">
      <static>true</static>
      <pose>{x:.2f} {y:.2f} 0 0 0 {rot_z:.2f}</pose>
      <link name="link">
{spheres}
      </link>
    </model>
'''
        xml += reg
        
    xml += '''
  </world>
</sdf>
'''
    with open('martian.world', 'w') as f:
        f.write(xml)

if __name__ == '__main__':
    generate_world()
