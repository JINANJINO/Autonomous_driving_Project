from setuptools import find_packages
from setuptools import setup

setup(
    name='midterm_msgs',
    version='0.0.0',
    packages=find_packages(
        include=('midterm_msgs', 'midterm_msgs.*')),
)
