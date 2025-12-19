#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import heapq
from collections import defaultdict, deque
from typing import List, Tuple, Set, Optional

import numpy as np
import rclpy
from rclpy.node import Node as RosNode
from rclpy.qos import QoSProfile, ReliabilityPolicy

from midterm_msgs.msg import SimpleGPS, SimpleLidar, Goal, WallList, Control
from geometry_msgs.msg import PoseStamped, Point
from nav_msgs.msg import Path
from visualization_msgs.msg import Marker, MarkerArray

# ================= Parameters =================

GRID_RES = 0.5
MAP_RANGE_X = (-150.0, 150.0)
MAP_RANGE_Y = (-150.0, 150.0)

# --- Perception (원래 A* 로직 복구) ---
# 장애물이 계속 있으면 점수가 올라가서 벽이 되고(Max 100),
# 사라지면 점수가 깎여서(Decay) 없어짐.
PROB_HIT = 10.0             # 한번 관측될 때 올라가는 점수 (적당히 설정하여 누적 유도)
PROB_DECAY_CANDIDATE = 2.0  # 관측 안 될 때 깎이는 점수
PROB_THRESH = 50.0          # 이 점수를 넘으면 '진짜 벽'으로 인정
PROB_MAX = 100.0
PROB_MIN = 0.0

INFLATE_HARD = 1            # 물리적 충돌 범위 (Grid)
INFLATE_SOFT = 2            # 안전 거리 (Cost penalty)
INFLATE_DYNAMIC = 1         # 동적 장애물 팽창 범위

# --- DWA ---
DWA_DT = 0.1
DWA_PREDICT_TIME = 2.0      
DWA_V_RES = 0.1
DWA_YAW_RES = 0.05
TARGET_SPEED_MAX = 20.0 / 3.6

COST_HEAD = 0.8             
COST_DIST = 1.0             
COST_VEL = 0.5
COST_OBS = 5.0              

# --- EKF ---
Q_DIAG = [0.1, 0.1, np.deg2rad(1.0), 1.0]
R_DIAG = [1.0, 1.0, np.deg2rad(10.0)]

# --- Control ---
MAX_STEER = np.deg2rad(45.0)
MAX_ACCEL = 2.0
ROBOT_RADIUS_M = 1.3

# LiDAR
LIDAR_MAX_RANGE = 30.0

FRAME_ID = "map"


def angle_mod(x: float) -> float:
    return (x + math.pi) % (2 * math.pi) - math.pi


def to_grid(x: float, y: float) -> Tuple[int, int]:
    return (int(round(x / GRID_RES)), int(round(y / GRID_RES)))


def from_grid(gx: int, gy: int) -> Tuple[float, float]:
    return (gx * GRID_RES, gy * GRID_RES)


# ============================================================
# 1. Perception: Probabilistic Map (A* Logic Restored)
# ============================================================
class ProbabilisticMap:
    def __init__(self):
        # (gx, gy) -> probability score (0.0 ~ 100.0)
        self.grid = defaultdict(float)
        self.confirmed: Set[Tuple[int, int]] = set()

    def update(self, hit_cells: Set[Tuple[int, int]], robot_footprint: Set[Tuple[int, int]]):
        """
        hit_cells: 현재 프레임의 라이다 히트 포인트
        robot_footprint: 로봇이 위치한 곳 (무조건 비워야 함)
        """
        
        # 1. Dynamic Inflation (라이다 점 부풀리기)
        inflated_hits = set()
        for (hx, hy) in hit_cells:
            inflated_hits.add((hx, hy))
            if INFLATE_DYNAMIC > 0:
                for dx in range(-INFLATE_DYNAMIC, INFLATE_DYNAMIC + 1):
                    for dy in range(-INFLATE_DYNAMIC, INFLATE_DYNAMIC + 1):
                        inflated_hits.add((hx + dx, hy + dy))

        # 2. Score Update (누적 및 감쇠)
        # 기존 그리드에 있는 모든 셀을 검사
        active_cells = list(self.grid.keys())
        
        for cell in active_cells:
            # 로봇 발밑은 무조건 0 (주행 중 자신이 벽이 되면 안됨)
            if cell in robot_footprint:
                del self.grid[cell]
                continue
            
            if cell in inflated_hits:
                # [누적] 계속 관측되면 점수 상승 -> 벽으로 굳어짐
                self.grid[cell] = min(PROB_MAX, self.grid[cell] + PROB_HIT)
            else:
                # [감쇠] 관측되지 않으면 점수 하락 -> 벽이 사라짐
                self.grid[cell] = max(PROB_MIN, self.grid[cell] - PROB_DECAY_CANDIDATE)
                # 점수가 너무 낮아지면 메모리에서 삭제
                if self.grid[cell] <= 0.1:
                    del self.grid[cell]

        # 3. 새로운 Hit 추가
        for cell in inflated_hits:
            if cell not in self.grid and cell not in robot_footprint:
                self.grid[cell] = PROB_HIT  # 초기 점수

        # 4. 확정 장애물 추출 (Threshold)
        # 이 confirmed set이 Global Planner에게 '벽'으로 전달됨
        self.confirmed.clear()
        for cell, score in self.grid.items():
            if score >= PROB_THRESH:
                self.confirmed.add(cell)
        
        return self.confirmed


# ============================================================
# 2. D* Lite Implementation (Original)
# ============================================================
class DStarLiteNode:
    __slots__ = ['x', 'y', 'k']
    def __init__(self, x, y, k=(0.0, 0.0)):
        self.x = x
        self.y = y
        self.k = k
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __lt__(self, other):
        return self.k < other.k

class GlobalPlanner:
    def __init__(self):
        self.known_walls = set()      
        self.static_walls = set()     
        
        self.x_dim = int((MAP_RANGE_X[1] - MAP_RANGE_X[0]) / GRID_RES) + 10
        self.y_dim = int((MAP_RANGE_Y[1] - MAP_RANGE_Y[0]) / GRID_RES) + 10
        self.off_x = int(-MAP_RANGE_X[0] / GRID_RES)
        self.off_y = int(-MAP_RANGE_Y[0] / GRID_RES)
        
        self.rhs = np.full((self.x_dim, self.y_dim), float('inf'))
        self.g = np.full((self.x_dim, self.y_dim), float('inf'))
        
        self.U = [] 
        self.km = 0.0
        
        self.start_grid = None
        self.goal_grid = None
        self.initialized = False
        self.last_start = None
        
        self.motions = [
            (1, 0, 1.0), (0, 1, 1.0), (-1, 0, 1.0), (0, -1, 1.0),
            (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)
        ]

    def _to_idx(self, gx, gy):
        return gx + self.off_x, gy + self.off_y

    def _from_idx(self, ix, iy):
        return ix - self.off_x, iy - self.off_y

    def _h(self, s, g):
        # Euclidean Heuristic
        return math.hypot(s[0] - g[0], s[1] - g[1])

    def _calculate_key(self, s):
        ix, iy = self._to_idx(s[0], s[1])
        g_val = self.g[ix, iy]
        rhs_val = self.rhs[ix, iy]
        min_val = min(g_val, rhs_val)
        return (min_val + self._h(s, self.start_grid) + self.km, min_val)

    def _update_vertex(self, u):
        ix, iy = self._to_idx(u[0], u[1])
        
        if u != self.goal_grid:
            min_rhs = float('inf')
            for dx, dy, cost in self.motions:
                s_prime = (u[0] + dx, u[1] + dy)
                if not self._is_valid(s_prime): continue
                
                c_val = cost
                # 벽이면 이동 불가
                if u in self.known_walls or s_prime in self.known_walls:
                    c_val = float('inf')
                
                six, siy = self._to_idx(s_prime[0], s_prime[1])
                min_rhs = min(min_rhs, c_val + self.g[six, siy])
            
            self.rhs[ix, iy] = min_rhs

        g_val = self.g[ix, iy]
        rhs_val = self.rhs[ix, iy]
        
        if g_val != rhs_val:
            heapq.heappush(self.U, DStarLiteNode(u[0], u[1], self._calculate_key(u)))

    def _compute_shortest_path(self):
        max_iter = 60000 
        count = 0
        
        six, siy = self._to_idx(self.start_grid[0], self.start_grid[1])
        
        while self.U:
            count += 1
            if count > max_iter: break
            
            u_node = self.U[0]
            k_old = u_node.k
            u = (u_node.x, u_node.y)
            
            start_k = self._calculate_key(self.start_grid)
            
            if k_old >= start_k and self.rhs[six, siy] == self.g[six, siy]:
                break

            heapq.heappop(self.U)
            ix, iy = self._to_idx(u[0], u[1])
            k_new = self._calculate_key(u)
            
            if k_old < k_new:
                heapq.heappush(self.U, DStarLiteNode(u[0], u[1], k_new))
            elif self.g[ix, iy] > self.rhs[ix, iy]:
                self.g[ix, iy] = self.rhs[ix, iy]
                for dx, dy, _ in self.motions:
                    s = (u[0] - dx, u[1] - dy)
                    if self._is_valid(s): self._update_vertex(s)
            else:
                self.g[ix, iy] = float('inf')
                self._update_vertex(u)
                for dx, dy, _ in self.motions:
                    s = (u[0] - dx, u[1] - dy)
                    if self._is_valid(s): self._update_vertex(s)

    def _is_valid(self, p):
        ix, iy = self._to_idx(p[0], p[1])
        return 0 <= ix < self.x_dim and 0 <= iy < self.y_dim

    # --- Interface ---
    
    def set_static_walls(self, walls):
        self.static_walls = walls
        self.known_walls.update(walls)

    def update_dynamic_walls(self, current_dynamic_walls):
        # 정적 벽 + 동적 장애물(확률적으로 굳어진 벽)
        current_total = self.static_walls | current_dynamic_walls
        
        added = current_total - self.known_walls
        removed = self.known_walls - current_total
        
        if not added and not removed:
            return False

        self.km += self._h(self.last_start, self.start_grid)
        self.last_start = self.start_grid

        changed = set()
        for w in added:
            self.known_walls.add(w)
            changed.add(w)
            for dx, dy, _ in self.motions:
                n = (w[0]+dx, w[1]+dy)
                if self._is_valid(n): changed.add(n)

        for w in removed:
            self.known_walls.remove(w)
            changed.add(w)
            for dx, dy, _ in self.motions:
                n = (w[0]+dx, w[1]+dy)
                if self._is_valid(n): changed.add(n)
        
        for u in changed:
            self._update_vertex(u)
            
        return True

    def _find_nearest_free(self, node):
        """벽(Static + Dynamic)에 갇혔을 때 탈출"""
        if node not in self.known_walls:
            return node
        q = deque([node])
        visited = {node}
        max_dist = 50
        count = 0
        while q:
            curr = q.popleft()
            count += 1
            if count > max_dist: break
            if curr not in self.known_walls: return curr
            for dx, dy, _ in self.motions:
                nxt = (curr[0]+dx, curr[1]+dy)
                if self._is_valid(nxt) and nxt not in visited:
                    visited.add(nxt)
                    q.append(nxt)
        return node

    def plan(self, start, goal):
        # 1. 맵 범위 제한
        safe_gx = np.clip(goal[0], MAP_RANGE_X[0]+1, MAP_RANGE_X[1]-1)
        safe_gy = np.clip(goal[1], MAP_RANGE_Y[0]+1, MAP_RANGE_Y[1]-1)
        
        # 2. 그리드 변환 & 벽 탈출(Snapping)
        curr_s = to_grid(start[0], start[1])
        curr_g = to_grid(safe_gx, safe_gy)
        
        # 동적 장애물까지 고려해서 갇혔으면 밖으로 꺼내줌
        curr_s = self._find_nearest_free(curr_s)
        curr_g = self._find_nearest_free(curr_g)

        # 3. D* Lite Init or Re-init
        if not self.initialized or self.goal_grid != curr_g:
            print(f"[D*] Init Goal: {curr_g}")
            self.start_grid = curr_s
            self.goal_grid = curr_g
            self.last_start = self.start_grid
            
            self.rhs.fill(float('inf'))
            self.g.fill(float('inf'))
            self.U = []
            self.km = 0.0
            
            gix, giy = self._to_idx(curr_g[0], curr_g[1])
            self.rhs[gix, giy] = 0
            heapq.heappush(self.U, DStarLiteNode(curr_g[0], curr_g[1], self._calculate_key(curr_g)))
            
            self.initialized = True
            self._compute_shortest_path()

        if self.start_grid != curr_s:
            self.start_grid = curr_s
            self._compute_shortest_path()

        # 4. Path Extraction (Gradient Descent)
        path = []
        curr = self.start_grid
        path.append(from_grid(curr[0], curr[1]))
        
        max_path_len = 5000
        six, siy = self._to_idx(curr[0], curr[1])
        
        # Start Node가 무한대면 경로 없음
        if self.g[six, siy] == float('inf'):
            return [] 

        while curr != self.goal_grid and len(path) < max_path_len:
            min_c = float('inf')
            nxt_n = None
            
            for dx, dy, cost in self.motions:
                nxt = (curr[0]+dx, curr[1]+dy)
                if not self._is_valid(nxt): continue
                if nxt in self.known_walls: continue
                
                nix, niy = self._to_idx(nxt[0], nxt[1])
                val = cost + self.g[nix, niy]
                
                if val < min_c:
                    min_c = val
                    nxt_n = nxt
                elif val == min_c and nxt_n:
                    if self._h(nxt, self.goal_grid) < self._h(nxt_n, self.goal_grid):
                        nxt_n = nxt
            
            if nxt_n:
                if from_grid(nxt_n[0], nxt_n[1]) in path: break
                curr = nxt_n
                path.append(from_grid(curr[0], curr[1]))
            else:
                break
        
        if len(path) > 3: path = path[::2]
        return path

    @property
    def combined_walls_set(self):
        return self.known_walls


# ============================================================
# 3. EKF
# ============================================================
class EKF:
    def __init__(self):
        self.x = np.zeros((4, 1)) 
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
            [0.0, 1.0, dt * v * math.cos(yaw), dt * math.sin(yaw)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        self.x[0, 0] += v * math.cos(yaw) * dt
        self.x[1, 0] += v * math.sin(yaw) * dt
        self.x[2, 0] += yaw_rate * dt
        self.x[3, 0] += accel * dt
        self.x[2, 0] = angle_mod(self.x[2, 0])
        self.P = F @ self.P @ F.T + self.Q

    def update(self, z):
        if not self.initialized:
            self.x = np.array([[z[0, 0]], [z[1, 0]], [z[2, 0]], [0.0]])
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
# 4. DWA
# ============================================================
class DWA:
    def __init__(self):
        self.pose = [0.0]*4

    def update_state(self, pose):
        self.pose = pose

    def predict(self, x, y, yaw, v, w):
        traj = []
        t = 0.0
        while t <= DWA_PREDICT_TIME:
            x += v * math.cos(yaw) * DWA_DT
            y += v * math.sin(yaw) * DWA_DT
            yaw += w * DWA_DT
            traj.append([x, y, yaw])
            t += DWA_DT
        return np.array(traj)

    def calc_control(self, global_path, obstacles):
        x, y, yaw, v = self.pose
        min_v = max(0.0, v - MAX_ACCEL * DWA_DT)
        max_v = min(TARGET_SPEED_MAX, v + MAX_ACCEL * DWA_DT)
        min_w = -np.deg2rad(60.0)
        max_w = np.deg2rad(60.0)

        look_pt = global_path[-1] if global_path else (x + 10.0, y)
        if global_path:
            for pt in global_path:
                if math.hypot(pt[0]-x, pt[1]-y) > 4.0:
                    look_pt = pt
                    break
        
        best_u = [0.0, 0.0]
        min_cost = float("inf")
        best_traj = []
        
        for tv in np.linspace(min_v, max_v, 6):
            for tw in np.linspace(min_w, max_w, 11):
                traj = self.predict(x, y, yaw, tv, tw)
                dx = look_pt[0] - traj[-1, 0]
                dy = look_pt[1] - traj[-1, 1]
                head_cost = abs(angle_mod(math.atan2(dy, dx) - traj[-1, 2]))
                dist_cost = math.hypot(dx, dy)
                vel_cost = (TARGET_SPEED_MAX - tv)
                
                obs_cost = 0.0
                for i in range(0, len(traj), 2):
                    gx, gy = to_grid(traj[i, 0], traj[i, 1])
                    if (gx, gy) in obstacles:
                        obs_cost = float("inf")
                        break
                    if INFLATE_SOFT > 0:
                        for sx in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                            for sy in range(-INFLATE_SOFT, INFLATE_SOFT+1):
                                if (gx+sx, gy+sy) in obstacles: 
                                    obs_cost += 5.0

                cost = COST_HEAD*head_cost + COST_DIST*dist_cost + COST_VEL*vel_cost + COST_OBS*obs_cost
                if cost < min_cost:
                    min_cost = cost
                    best_u = [tv, tw]
                    best_traj = traj
                    
        return best_u, best_traj, []


# ============================================================
# 5. Integrated Planner Node (RViz Output)
# ============================================================
class IntegratedPlannerRViz(RosNode):
    def __init__(self):
        super().__init__("integrated_planner_rviz")
        self.ekf = EKF()
        self.pmap = ProbabilisticMap()
        self.global_planner = GlobalPlanner()
        self.local_planner = DWA()
        
        self.pose = np.zeros((4, 1))
        self.lidar_scan = []
        self.goal = None
        self.global_path = []

        qos = QoSProfile(depth=10)
        lidar_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)

        self.create_subscription(SimpleGPS, "/gps_1", self.gps_cb, qos)
        self.create_subscription(SimpleLidar, "/lidar", self.lidar_cb, lidar_qos)
        self.create_subscription(Goal, "/goal", self.goal_cb, qos)
        self.create_subscription(WallList, "/walls", self.walls_cb, qos)
        self.ctrl_pub = self.create_publisher(Control, "/control", qos)

        self.path_pub = self.create_publisher(Path, "/global_path", qos)
        self.pose_pub = self.create_publisher(PoseStamped, "/vehicle_pose", qos)
        self.wall_marker_pub = self.create_publisher(MarkerArray, "/wall_markers", qos)
        self.dynamic_marker_pub = self.create_publisher(Marker, "/dynamic_obs_markers", qos)
        self.lidar_marker_pub = self.create_publisher(Marker, "/lidar_points", qos)
        self.car_marker_pub = self.create_publisher(Marker, "/car_model", qos)

        self.static_walls_world = []
        self.create_timer(0.1, self.control_loop)

    def gps_cb(self, msg):
        z = np.array([[msg.x], [msg.y], [angle_mod(msg.yaw)]])
        self.ekf.update(z)
        self.pose = self.ekf.x
        
        ps = PoseStamped()
        ps.header.frame_id = FRAME_ID
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = float(self.pose[0])
        ps.pose.position.y = float(self.pose[1])
        ps.pose.orientation.z = math.sin(self.pose[2]/2)
        ps.pose.orientation.w = math.cos(self.pose[2]/2)
        self.pose_pub.publish(ps)

    def lidar_cb(self, msg): self.lidar_scan = list(msg.beams)
    
    def goal_cb(self, msg): 
        self.goal = (msg.x, msg.y)
        self.get_logger().info(f"New Goal Received: {self.goal}")

    def walls_cb(self, msg):
        static = set()
        self.static_walls_world = []
        for w in msg.walls:
            gx_min, gy_min = to_grid(w.bl_x, w.bl_y)
            gx_max, gy_max = to_grid(w.bl_x+w.size_x, w.bl_y+w.size_y)
            for x in range(gx_min - INFLATE_HARD, gx_max + INFLATE_HARD):
                for y in range(gy_min - INFLATE_HARD, gy_max + INFLATE_HARD):
                    static.add((x,y))
            self.static_walls_world.append((w.bl_x, w.bl_y, w.size_x, w.size_y))
        
        self.global_planner.set_static_walls(static)
        self.publish_static_walls()

    def publish_static_walls(self):
        ma = MarkerArray()
        for i, (x, y, sx, sy) in enumerate(self.static_walls_world):
            m = Marker(ns="walls", id=i, type=Marker.CUBE, action=Marker.ADD)
            m.header.frame_id = FRAME_ID
            m.pose.position.x = x + sx/2
            m.pose.position.y = y + sy/2
            m.scale.x, m.scale.y, m.scale.z = sx, sy, 1.0
            m.color.r, m.color.g, m.color.b, m.color.a = 0.5, 0.5, 0.5, 0.5
            ma.markers.append(m)
        self.wall_marker_pub.publish(ma)

    def publish_dynamic_obs(self, cells):
        m = Marker(ns="dyn", id=0, type=Marker.CUBE_LIST, action=Marker.ADD)
        m.header.frame_id = FRAME_ID
        m.scale.x, m.scale.y, m.scale.z = GRID_RES, GRID_RES, 0.5
        m.color.r, m.color.a = 1.0, 0.8
        for (gx, gy) in cells:
            wx, wy = from_grid(gx, gy)
            p = Point(x=wx, y=wy, z=0.0)
            m.points.append(p)
        self.dynamic_marker_pub.publish(m)

    def publish_car(self, x, y, yaw):
        m = Marker(ns="car", id=0, type=Marker.CUBE, action=Marker.ADD)
        m.header.frame_id = FRAME_ID
        m.pose.position.x, m.pose.position.y, m.pose.position.z = x, y, 0.5
        m.pose.orientation.z = math.sin(yaw/2)
        m.pose.orientation.w = math.cos(yaw/2)
        m.scale.x, m.scale.y, m.scale.z = 4.5, 2.0, 1.5
        m.color.r, m.color.g, m.color.b, m.color.a = 0.0, 0.0, 1.0, 1.0
        self.car_marker_pub.publish(m)

    def publish_global_path(self):
        msg = Path()
        msg.header.frame_id = FRAME_ID
        msg.header.stamp = self.get_clock().now().to_msg()
        for (px, py) in self.global_path:
            p = PoseStamped()
            p.header = msg.header
            p.pose.position.x, p.pose.position.y = px, py
            msg.poses.append(p)
        self.path_pub.publish(msg)

    def publish_lidar_markers(self, x, y, yaw):
        m = Marker(ns="lidar", id=0, type=Marker.POINTS, action=Marker.ADD)
        m.header.frame_id = FRAME_ID
        m.scale.x, m.scale.y = 0.1, 0.1
        m.color.r, m.color.g, m.color.b, m.color.a = 0.0, 1.0, 0.0, 0.6
        
        angle_inc = 2.0 * math.pi / len(self.lidar_scan) if self.lidar_scan else 0
        for i, r in enumerate(self.lidar_scan):
            if 0.2 < r < LIDAR_MAX_RANGE:
                theta = angle_mod(yaw + i*angle_inc)
                wx = x + r * math.cos(theta)
                wy = y + r * math.sin(theta)
                p = Point(x=wx, y=wy, z=0.2)
                m.points.append(p)
        self.lidar_marker_pub.publish(m)

    def control_loop(self):
        if not self.ekf.initialized: return
        if self.goal is None: return

        x, y, yaw, v = self.pose.flatten()

        # 1. Perception
        hits = set()
        if self.lidar_scan:
            angle_inc = 2.0 * math.pi / len(self.lidar_scan)
            for i, r in enumerate(self.lidar_scan):
                if 0.2 < r < LIDAR_MAX_RANGE:
                    theta = angle_mod(yaw + i*angle_inc)
                    wx = x + r * math.cos(theta)
                    wy = y + r * math.sin(theta)
                    hits.add(to_grid(wx, wy))
        
        footprint = set()
        rcx, rcy = to_grid(x, y)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                footprint.add((rcx+dx, rcy+dy))
        
        confirmed_obs = self.pmap.update(hits, footprint)
        
        # 2. Global Plan (D* Lite)
        self.global_planner.update_dynamic_walls(confirmed_obs)
        self.global_path = self.global_planner.plan((x,y), self.goal)
        
        # 3. Local Plan & Control
        self.local_planner.update_state([x,y,yaw,v])
        combined = self.global_planner.combined_walls_set
        uv, _, _ = self.local_planner.calc_control(self.global_path, combined)
        
        accel = 1.0 * (uv[0] - v)
        steer = math.atan2(uv[1]*2.5, v+0.1)
        
        msg = Control()
        msg.accel = float(np.clip(accel, -1.0, 1.0))
        msg.steering = float(np.clip(steer, -MAX_STEER, MAX_STEER))
        self.ctrl_pub.publish(msg)
        self.ekf.predict(np.array([[msg.accel], [msg.steering]]), 0.1)

        # 4. Viz
        self.publish_global_path()
        self.publish_dynamic_obs(confirmed_obs)
        self.publish_car(x, y, yaw)
        self.publish_lidar_markers(x, y, yaw)

def main(args=None):
    rclpy.init(args=args)
    node = IntegratedPlannerRViz()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__":
    main()