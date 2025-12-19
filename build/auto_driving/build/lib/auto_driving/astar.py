#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobility and Intelligence - Optimized Parameters
Author: J-H LEE
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from collections import deque, defaultdict
import heapq
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from midterm_msgs.msg import SimpleGPS, SimpleLidar, Goal, WallList, Control

# ================= Parameters (Optimized) =================

# --- Grid / Map ---
GRID_RES = 0.5          
MAP_RANGE_X = (-120, 120) 
MAP_RANGE_Y = (-120, 120) 

# --- Perception (노이즈 빠른 제거) ---
PROB_HIT = 20.0         
PROB_DECAY_CANDIDATE = 15.0  # [상향] 잔상(Ghost Wall)이 더 빨리 사라지게 함
PROB_THRESH = 80.0      
PROB_MAX = 100.0

# --- Inflation (벽 긁기 방지) ---
INFLATE_HARD = 1      # 물리적 충돌 (0.5m)
INFLATE_SOFT = 2      # [조정] 너무 넓지 않게 하여 좁은 길 통과 허용
SAFETY_COST = 40.0    # [상향] 대신 벽 근처 페널티를 강화하여 크게 돌도록 유도

INFLATE_DYNAMIC = 1     

# --- DWA (Local Planner - 부드러운 코너링) ---
DWA_DT = 0.1
# [핵심] 예측 시간을 늘려 코너를 미리 보고 감속 유도
DWA_PREDICT_TIME = 2.5 

DWA_V_RES = 0.05
DWA_YAW_RES = 0.05
TARGET_SPEED_MAX = 15.0 / 3.6 

# --- Cost Weights (안전 제일) ---
COST_HEAD = 1.0        # [상향] 경로 방향 정렬을 최우선 (코너에서 머리 돌리기)
COST_DIST = 0.5        
COST_VEL = 0.15        # [하향] 속도 욕심을 줄여서 코너에서 감속 허용
COST_OBS = 3.5         # [조정] 장애물 회피 밸런스

# --- EKF ---
Q_DIAG = [0.1, 0.1, np.deg2rad(1.0), 1.0]
R_DIAG = [1.0, 1.0, np.deg2rad(10.0)]

# --- Control ---
MAX_STEER = np.deg2rad(45.0)
MAX_ACCEL = 1.5
VIZ_OBS_SIZE = 5      
VIZ_ROBOT_SIZE = 8    
ROBOT_RADIUS_M = 1.3  

# ---------------------------------------------

def angle_mod(x):
    return (x + np.pi) % (2 * np.pi) - np.pi

def to_grid(x, y):
    return (int(round(x / GRID_RES)), int(round(y / GRID_RES)))

def from_grid(gx, gy):
    return (gx * GRID_RES, gy * GRID_RES)

# ============================================================
# 1. EKF
# ============================================================
class EKF:
    def __init__(self):
        self.x = np.zeros((4, 1)) # x, y, yaw, v
        self.P = np.eye(4)
        self.Q = np.diag(np.square(Q_DIAG))
        self.R = np.diag(np.square(R_DIAG))
        self.initialized = False

    def predict(self, u, dt):
        if not self.initialized: return
        v = self.x[3, 0]
        yaw = self.x[2, 0]
        accel, steer = u
        WB = 2.5
        yaw_rate = (v / WB) * math.tan(steer)

        F = np.array([
            [1.0, 0.0, -dt * v * math.sin(yaw), dt * math.cos(yaw)],
            [0.0, 1.0,  dt * v * math.cos(yaw), dt * math.sin(yaw)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        
        self.x[0, 0] += v * math.cos(yaw) * dt
        self.x[1, 0] += v * math.sin(yaw) * dt
        self.x[2, 0] += yaw_rate * dt
        self.x[3, 0] += accel * dt
        self.x[2, 0] = angle_mod(self.x[2, 0])
        self.P = F @ self.P @ F.T + self.Q

    def update(self, z):
        if not self.initialized:
            self.x = np.array([[z[0,0]], [z[1,0]], [z[2,0]], [0.0]])
            self.P = np.eye(4)
            self.initialized = True
            return
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
        z_pred = H @ self.x
        y = z - z_pred
        y[2, 0] = angle_mod(y[2, 0])
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.x[2, 0] = angle_mod(self.x[2, 0])
        self.P = (np.eye(4) - K @ H) @ self.P

# ============================================================
# 2. Probabilistic Map
# ============================================================
class ProbabilisticMap:
    def __init__(self):
        self.grid = defaultdict(float) 
        self.confirmed = set() 

    def update(self, hit_cells, robot_grid_footprint):
        inflated_hits = set()
        if INFLATE_DYNAMIC > 0:
            for (hx, hy) in hit_cells:
                for dx in range(-INFLATE_DYNAMIC, INFLATE_DYNAMIC+1):
                    for dy in range(-INFLATE_DYNAMIC, INFLATE_DYNAMIC+1):
                        inflated_hits.add((hx+dx, hy+dy))
        else:
            inflated_hits = hit_cells

        keys_to_check = list(self.grid.keys())
        for cell in keys_to_check:
            # 로봇 위치 Clearing
            if cell in robot_grid_footprint:
                del self.grid[cell]
                continue
            
            # Decay Logic (잔상 제거)
            if cell not in inflated_hits:
                score = self.grid[cell]
                # 확정되지 않은 장애물은 빠르게 점수 삭감
                if score < PROB_THRESH: 
                    self.grid[cell] -= PROB_DECAY_CANDIDATE
                    if self.grid[cell] <= 0:
                        del self.grid[cell]

        # Hit Logic (장애물 누적)
        for cell in inflated_hits:
            if cell in robot_grid_footprint: continue
            self.grid[cell] = min(PROB_MAX, self.grid[cell] + PROB_HIT)

        # Thresholding
        self.confirmed.clear()
        for cell, score in self.grid.items():
            if score >= PROB_THRESH:
                self.confirmed.add(cell)
        
        return self.confirmed

# ============================================================
# 3. Global Planner (A*)
# ============================================================
class GlobalPlanner:
    def __init__(self):
        self.static_walls = set()
        self.combined_walls = set()
        
    def set_static_walls(self, walls):
        self.static_walls = walls
        self.combined_walls = walls.copy()

    def update_dynamic_walls(self, dyn_walls):
        self.combined_walls = self.static_walls | dyn_walls

    def plan(self, start, goal):
        start_node = to_grid(start[0], start[1])
        goal_node = to_grid(goal[0], goal[1])
        
        if start_node in self.combined_walls:
             start_node = self._find_nearest_free(start_node)

        open_set = []
        heapq.heappush(open_set, (0, start_node))
        came_from = {}
        g_score = {start_node: 0}
        
        H_WEIGHT = 1.2
        max_iter = 40000 
        count = 0
        final_node = None
        
        while open_set:
            count += 1
            if count > max_iter: break 
            
            _, current = heapq.heappop(open_set)
            
            if current == goal_node or math.hypot(current[0]-goal_node[0], current[1]-goal_node[1]) < 2.0:
                final_node = current
                break
                
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                neighbor = (current[0]+dx, current[1]+dy)
                
                # Hard Collision
                if neighbor in self.combined_walls: continue
                
                move_cost = 1.0 if (dx*dy==0) else 1.414
                
                # Soft Padding Cost (안전 구역)
                soft_penalty = 0.0
                if INFLATE_SOFT > 0:
                    for sx in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                        for sy in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                            if (neighbor[0]+sx, neighbor[1]+sy) in self.combined_walls:
                                soft_penalty = SAFETY_COST
                                break
                        if soft_penalty > 0: break
                
                tentative_g = g_score[current] + move_cost + soft_penalty
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + H_WEIGHT * self._h(neighbor, goal_node)
                    heapq.heappush(open_set, (f, neighbor))
        
        path = []
        if final_node:
            curr = final_node
            while curr in came_from:
                path.append(from_grid(curr[0], curr[1]))
                curr = came_from[curr]
            path.append(from_grid(start_node[0], start_node[1]))
            path.reverse()
            if len(path) > 3: path = path[::2] 
                
        return path

    def _h(self, a, b):
        return math.hypot(a[0]-b[0], a[1]-b[1])
    
    def _find_nearest_free(self, node):
        q = deque([node])
        visited = {node}
        while q:
            curr = q.popleft()
            if curr not in self.combined_walls: return curr
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                neighbor = (curr[0]+dx, curr[1]+dy)
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
            if len(visited) > 200: break
        return node

# ============================================================
# 4. DWA
# ============================================================
class DWA:
    def __init__(self):
        self.pose = [0,0,0,0]

    def update_state(self, pose):
        self.pose = pose

    def calc_control(self, global_path, obstacles):
        x, y, yaw, v = self.pose
        
        min_v = max(0.0, v - MAX_ACCEL * DWA_DT)
        max_v = min(TARGET_SPEED_MAX, v + MAX_ACCEL * DWA_DT)
        min_w = -np.deg2rad(60.0)
        max_w =  np.deg2rad(60.0)

        look_pt = global_path[-1] if global_path else (x+5, y)
        if global_path:
            for pt in global_path:
                if math.hypot(pt[0]-x, pt[1]-y) > 3.0:
                    look_pt = pt
                    break
        
        best_u = [0.0, 0.0]
        min_cost = float('inf')
        best_traj = []
        all_trajs = []

        for tv in np.linspace(min_v, max_v, 5):
            for tw in np.linspace(min_w, max_w, 9):
                traj = self.predict(x, y, yaw, tv, tw)
                
                dx = look_pt[0] - traj[-1,0]
                dy = look_pt[1] - traj[-1,1]
                
                head_cost = abs(angle_mod(math.atan2(dy, dx) - traj[-1,2]))
                dist_cost = math.hypot(dx, dy)
                vel_cost = (TARGET_SPEED_MAX - tv)
                
                obs_cost = 0.0
                for i in range(0, len(traj), 2): 
                    gx, gy = to_grid(traj[i,0], traj[i,1])
                    if (gx, gy) in obstacles:
                        obs_cost = float('inf')
                        break
                    
                    if INFLATE_SOFT > 0:
                        for sx in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                            for sy in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                                if (gx+sx, gy+sy) in obstacles:
                                    obs_cost += 10.0
                
                cost = COST_HEAD*head_cost + COST_DIST*dist_cost + COST_VEL*vel_cost + COST_OBS*obs_cost
                all_trajs.append(traj)
                
                if cost < min_cost:
                    min_cost = cost
                    best_u = [tv, tw]
                    best_traj = traj
                    
        return best_u, best_traj, all_trajs

    def predict(self, x, y, yaw, v, w):
        traj = []
        t = 0
        while t <= DWA_PREDICT_TIME:
            x += v * math.cos(yaw) * DWA_DT
            y += v * math.sin(yaw) * DWA_DT
            yaw += w * DWA_DT
            traj.append([x, y, yaw])
            t += DWA_DT
        return np.array(traj)

# ============================================================
# 5. Integrated Planner Node
# ============================================================
class IntegratedPlanner(Node):
    def __init__(self):
        super().__init__('integrated_planner')
        
        self.ekf = EKF()
        self.pmap = ProbabilisticMap()
        self.global_planner = GlobalPlanner()
        self.local_planner = DWA()
        
        self.pose = np.zeros((4,1))
        self.lidar_scan = []
        self.goal = None
        self.global_path = []
        
        self.create_subscription(SimpleGPS, '/gps_1', self.gps_cb, 10)
        self.create_subscription(SimpleLidar, '/lidar', self.lidar_cb, QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_subscription(Goal, '/goal', self.goal_cb, 10)
        self.create_subscription(WallList, '/walls', self.walls_cb, 10)
        self.pub_ctrl = self.create_publisher(Control, '/control', 10)
        
        self.create_timer(0.1, self.control_loop)
        
        # --- Dual Visualization Setup ---
        plt.ion()
        self.fig, (self.ax_global, self.ax_local) = plt.subplots(1, 2, figsize=(14, 7))
        
        # 1. Global View
        self.ax_global.set_title("Global Map (Fixed View)")
        self.ax_global.set_xlim(MAP_RANGE_X)
        self.ax_global.set_ylim(MAP_RANGE_Y)
        self.ax_global.set_aspect('equal')
        self.ax_global.grid(True, alpha=0.3)
        self.ln_g_static, = self.ax_global.plot([], [], 'ks', markersize=3, label='Static')
        self.sc_g_dynamic = self.ax_global.scatter([], [], c='orange', s=VIZ_OBS_SIZE, marker='s', label='Dynamic')
        self.ln_g_path, = self.ax_global.plot([], [], 'b--', linewidth=2, label='Global Path')
        self.ln_g_robot, = self.ax_global.plot([], [], 'bo', markersize=VIZ_ROBOT_SIZE, label='Robot')
        self.ax_global.legend(loc='upper right', fontsize='small')

        # 2. Local View
        self.ax_local.set_title("Local Planner (DWA Zoom ±15m)")
        self.ax_local.set_aspect('equal')
        self.ax_local.grid(True, alpha=0.5)
        self.ln_l_dwa_cands, = self.ax_local.plot([], [], 'g-', alpha=0.15, linewidth=1)
        self.ln_l_dwa_best, = self.ax_local.plot([], [], 'r-', linewidth=2.5, label='DWA Best')
        self.ln_l_path_seg, = self.ax_local.plot([], [], 'b--', linewidth=2, label='Global Ref')
        self.ln_l_robot, = self.ax_local.plot([], [], 'bo', markersize=10, label='Robot')
        self.sc_l_obs = self.ax_local.scatter([], [], c='k', s=20, marker='s')
        self.circ_clearing = plt.Circle((0,0), ROBOT_RADIUS_M, color='cyan', fill=False, linestyle=':', label='Clearing')
        self.ax_local.add_patch(self.circ_clearing)
        self.ax_local.legend(loc='upper right', fontsize='small')

        plt.show()

    def gps_cb(self, msg):
        z = np.array([[msg.x], [msg.y], [angle_mod(msg.yaw)]])
        self.ekf.update(z)
        self.pose = self.ekf.x

    def lidar_cb(self, msg):
        self.lidar_scan = msg.beams

    def goal_cb(self, msg):
        self.goal = (msg.x, msg.y)

    def walls_cb(self, msg):
        static = set()
        vis_x, vis_y = [], []
        for w in msg.walls:
            gx_min, gy_min = to_grid(w.bl_x, w.bl_y)
            gx_max, gy_max = to_grid(w.bl_x + w.size_x, w.bl_y + w.size_y)
            for x in range(gx_min - INFLATE_HARD, gx_max + INFLATE_HARD):
                for y in range(gy_min - INFLATE_HARD, gy_max + INFLATE_HARD):
                    static.add((x,y))
                    if x % 2 == 0 and y % 2 == 0:
                        vis_x.append(x * GRID_RES)
                        vis_y.append(y * GRID_RES)
        self.global_planner.set_static_walls(static)
        self.ln_g_static.set_data(vis_x, vis_y)

    def control_loop(self):
        if not self.ekf.initialized or self.goal is None: return
        x, y, yaw, v = self.pose.flatten()
        
        # 1. Perception
        hits = set()
        if self.lidar_scan:
            angle_inc = 2 * np.pi / len(self.lidar_scan)
            
            for i, r in enumerate(self.lidar_scan):
                if 0.2 < r < 30.0:
                    theta = angle_mod(yaw + i * angle_inc)
                    wx = x + r * math.cos(theta)
                    wy = y + r * math.sin(theta)
                    hits.add(to_grid(wx, wy))
        
        # Clearing
        footprint = set()
        rcx, rcy = to_grid(x, y)
        c_range = int(ROBOT_RADIUS_M / GRID_RES) + 1
        for dx in range(-c_range, c_range+1):
            for dy in range(-c_range, c_range+1):
                footprint.add((rcx+dx, rcy+dy))

        confirmed_obs = self.pmap.update(hits, footprint)
        
        # 2. Global Plan
        self.global_planner.update_dynamic_walls(confirmed_obs)
        self.global_path = self.global_planner.plan((x,y), self.goal)
        
        # 3. Local Plan
        self.local_planner.update_state([x,y,yaw,v])
        combined = self.global_planner.combined_walls
        uv, best_traj, all_trajs = self.local_planner.calc_control(self.global_path, combined)
        
        # 4. Control
        accel = 1.0 * (uv[0] - v)
        steer = math.atan(uv[1] * 2.5 / (v + 0.1))
        
        msg = Control()
        msg.accel = float(np.clip(accel, -1.0, 1.0))
        msg.steering = float(np.clip(steer, -MAX_STEER, MAX_STEER))
        self.pub_ctrl.publish(msg)
        self.ekf.predict(np.array([[msg.accel], [msg.steering]]), 0.1)
        
        # 5. Visualize
        self.visualize_dual(x, y, confirmed_obs, all_trajs, best_traj)

    def visualize_dual(self, x, y, obstacles, dwa_trajs, best_traj):
        # Global
        if self.global_path:
            self.ln_g_path.set_data([p[0] for p in self.global_path], [p[1] for p in self.global_path])
        else:
            self.ln_g_path.set_data([], [])
        
        if obstacles:
            ox = [gx*GRID_RES for gx, gy in obstacles]
            oy = [gy*GRID_RES for gx, gy in obstacles]
            self.sc_g_dynamic.set_offsets(np.c_[ox, oy])
        else:
            self.sc_g_dynamic.set_offsets(np.empty((0,2)))
        self.ln_g_robot.set_data([x], [y])
        
        # Local
        self.ax_local.set_xlim(x - 15, x + 15)
        self.ax_local.set_ylim(y - 15, y + 15)
        d_x, d_y = [], []
        for tr in dwa_trajs[::3]:
            d_x.extend(tr[:,0]); d_x.append(np.nan)
            d_y.extend(tr[:,1]); d_y.append(np.nan)
        self.ln_l_dwa_cands.set_data(d_x, d_y)
        if len(best_traj) > 0:
            self.ln_l_dwa_best.set_data(best_traj[:,0], best_traj[:,1])
        
        if self.global_path:
             seg_x = [p[0] for p in self.global_path if abs(p[0]-x)<20 and abs(p[1]-y)<20]
             seg_y = [p[1] for p in self.global_path if abs(p[0]-x)<20 and abs(p[1]-y)<20]
             self.ln_l_path_seg.set_data(seg_x, seg_y)
        else:
             self.ln_l_path_seg.set_data([], [])
             
        self.ln_l_robot.set_data([x], [y])
        self.circ_clearing.center = (x, y)
        self.circ_clearing.radius = ROBOT_RADIUS_M
        
        if obstacles:
            self.sc_l_obs.set_offsets(np.c_[ox, oy])
        else:
            self.sc_l_obs.set_offsets(np.empty((0,2)))

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

def main(args=None):
    rclpy.init(args=args)
    node = IntegratedPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()