from setuptools import find_packages,setup
from glob import glob
import os
n='onsemi_gemma_vla'
setup(name=n,version='1.0.0',packages=find_packages(),data_files=[('share/ament_index/resource_index/packages',['resource/'+n]),('share/'+n,['package.xml']),(os.path.join('share',n,'launch'),glob('launch/*.launch.py'))],install_requires=['setuptools'],zip_safe=True,maintainer='Vishal Agrawal',maintainer_email='vishal.agrawal@onsemi.com',description='Gemma VLA using ROS camera',license='Apache-2.0',entry_points={'console_scripts':['frame_bridge=onsemi_gemma_vla.frame_bridge:main']})
