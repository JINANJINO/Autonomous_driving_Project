from setuptools import find_packages, setup

package_name = 'auto_driving'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jinhan',
    maintainer_email='jinhan3579@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'astar = auto_driving.astar:main',
            'dstar_hard = auto_driving.dstar_hard:main',
            'dstar_lite = auto_driving.dstar_lite:main',
        ],
    },
)
