import os
from glob import glob
from setuptools import setup
package_name = 'onsemi_itof'
setup(
    name=package_name, version='0.0.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Vishal Agrawal', maintainer_email='vishal.agrawal@onsemi.com',
    description='DepthVista iToF camera publisher (depth/IR to ROS 2 topics).',
    license='Proprietary', tests_require=['pytest'],
    entry_points={'console_scripts': [
        'itof_publisher = onsemi_itof.itof_publisher_node:main',
    ]},
)
