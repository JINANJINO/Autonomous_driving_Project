# Autonomous driving Simulation
This repository is a code that allows you to drive autonomously using the code you wrote through Ros in a Grid World environment.
First of all, I would like you to adjust the settings to suit your environment.

## 1. Setting
First, create your workspace and the ```src``` directory, and then copy the ```midterm_env``` and
```midterm_msg``` packages from the current repository into the ```src``` directory.
Before proceeding with the package build, please set the code section below to suit your environment.

```python
self.GOAL_FILE_PATH = "/home/jinhan/mid_mobiity/src/env/env/midterm_env/midterm_env/goal.txt"
self.WALL_FILE_PATH = "/home/jinhan/mid_mobiity/src/env/env/midterm_env/midterm_env/wall.txt"
self.OBSTACLE_FILE_PATH = "/home/jinhan/mid_mobiity/src/env/env/midterm_env/midterm_env/obstacle.txt"
```
If you have completed the settings, you can proceed with the build.

> If the following Python packages do not exist in your environment, you will need to install them additionally.
```
pip install shapely
```
After completing the settings, run the following command: 
```
ros2 run midterm_env env
```
Additionally, something you may want to know about this environment is that if you run the node and the **window size** is small, you can modify the following code within the ```env```environment.

```python
self.WINDOW_SIZE = 200
```
And here, you can set the **goal** point or **map** as you like by editing the ```goal.txt```, ```wall.txt```, and ```obstacle.txt``` files. As an example, I have created contents related to **easy**, **normal**, and **hard** in the repository.

---

## 2. Algorithm for autonomous driving
The algorithm for the ```auto_driving``` package currently included in the repository is as follows.
**Localization** is an extension of the previously discussed ```Bayes filter```, which allows the use of the ```EKF (Extended Kalman filter)```, which uses a nonlinear model.
And as you can see when you open the **Hard map**, there are very long obstacles, like walls, that are not captured on the map. To overcome this, we structured the code so that areas recognized as walls within the Lidar would remain on the map, utilizing **probabilistic methods** to ensure that highly reliable areas would 
remain.
For **Global Planner**, ```A* algorithm``` was used. And for **Local Planner**, **DWA (Dynamic Window Approach)** method was used.


> I encourage you to actively experiment with various algorithms, such as ```RRT```, ```RRT*```, and ```D* lite```.
> You could also consider utilizing ```Euclidian Clustering``` for preprocessing sensor data. To try these out, simply create a new Python file and modify ```setup.py``` to test your code.



https://github.com/user-attachments/assets/73f25b03-1de3-489b-b92a-5c4c00b0ebe7


