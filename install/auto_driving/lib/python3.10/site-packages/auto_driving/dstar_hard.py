#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Planner (Fixed) — D* Lite + DWA
- Fixed: Added missing '_pick_local_subgoal' method
Author: J-H LEE (modified)
"""

import math
from collections import deque, defaultdict
from typing import Optional, Tuple, List, Set

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from enum import Enum

import rclpy
from rclpy.node import Node as RosNode
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from std_msgs.msg import Bool
from midterm_msgs.msg import SimpleGPS, SimpleLidar, Goal, WallList, Control

# ===================== Safety/Planning Parameters =====================
GRID_RES = 1.0  
INFLATE_CELLS = 3  
FRONT_ARC_DEG = 170  
FRONT_STOP_DEG = 55
FRONT_STOP_HARD = 2.6
FRONT_STOP_SOFT = 5.5

LOOKAHEAD_MIN = 8.0
LOOKAHEAD_MAX = 20.0
TIME_HEADWAY_SEC = 0.9
LD_SMOOTH_TAU = 0.9
MAX_STEER_RATE_DPS = 30.0
MAX_TARGET_SPEED = 8.0 / 3.6
MARGIN_METERS = 80.0  

STANLEY_CTE_GAIN = 0.7
STANLEY_BLEND = 0.65
STANLEY_V_EPS = 0.6

YAW_DAMP_K = 0.20

DYN_PERSIST_K = 4
DYN_CONFIRM_M = 2
DYN_RELEASE_FRAMES = 20  
DYN_INFLATE_CELLS = 0
GOAL_MASK_R_CELLS = 3
LATERAL_ACC_MAX = 1.5

DYN_HARDIFY_SEC = 0.20
DYN_HARD_INFLATE_CELLS = 4
DYN_HARD_DECAY_STEPS = 3

LIDAR_MAX = 20.0
LIDAR_MIN = 0.20
FAST_ADD_DIST = 4.0  

SOFT_COST_PENALTY = 500.0

BACKTRACK_TRAIL_HORIZON_SEC = 25.0
BACKTRACK_SAMPLE_DIST_M = 0.75
BACKTRACK_PENALTY_MAX = 120.0
BACKTRACK_PENALTY_DECAY_SEC = 12.0
BACKTRACK_EXCLUDE_RECENT = 4

COLLISION_STRIKE_LIMIT = 6
COLLISION_COOLDOWN_SEC = 0.1
LOCAL_ONLY_RECOVER_SEC = 30.0
FRONT_CLEAR_FOR_RECOVER = 9.0

EMERGENCY_STRIKE_LIMIT = 10
EMERGENCY_MIN_HOLD_SEC = 1.5
EMERGENCY_INFLATE_CELLS = 2
EMERGENCY_REPLAN_ITERS = 15000

Q_DIAG = np.array([0.1, 0.1, np.deg2rad(1.2), 1.2]) ** 2
R_DIAG = np.array([0.7, 0.7, np.deg2rad(5.0)]) ** 2

OFFMAP_PERSIST_K = max(DYN_PERSIST_K, 8)
OFFMAP_CONFIRM_M = max(DYN_CONFIRM_M, 3)
OFFMAP_RELEASE_FRAMES = max(DYN_RELEASE_FRAMES, 80)
OFFMAP_INFLATE_CELLS = max(DYN_INFLATE_CELLS, 0)

VIZ_WALL_EDGE = 'dimgray'
VIZ_WALL_FACE = 'lightgray'

qos_profile = QoSProfile(depth=10)
qos_sensor = QoSProfile(depth=1)
qos_sensor.reliability = ReliabilityPolicy.BEST_EFFORT
qos_sensor.history = HistoryPolicy.KEEP_LAST
qos_sensor.durability = DurabilityPolicy.VOLATILE


# ----------------- utils -----------------
def angle_mod(x: float) -> float:
    return (x + np.pi) % (2 * np.pi) - np.pi

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def to_grid_cell(xy_m):
    return (int(round(xy_m[0] / GRID_RES)), int(round(xy_m[1] / GRID_RES)))

def from_grid_cell(cell):
    return (cell[0] * GRID_RES, cell[1] * GRID_RES)

def inflate_cells(cells: Set[tuple], r: int) -> Set[tuple]:
    if r <= 0:
        return set(cells)
    out = set()
    for (gx, gy) in cells:
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                out.add((gx + dx, gy + dy))
    return out


# ============================================================
# EKF
# ============================================================
class EKF:
    def __init__(self, q_diag: np.ndarray, r_diag: np.ndarray):
        self.Q = np.diag(q_diag.astype(float))
        self.R = np.diag(r_diag.astype(float))
        self.x = np.zeros((4, 1))
        self.P = np.eye(4)
        self.initialized = False

    def _motion_model(self, x, u, dt):
        F = np.array([
            [1.0, 0, 0, 0],
            [0, 1.0, 0, 0],
            [0, 0, 1.0, 0],
            [0, 0, 0, 0]
        ], dtype=float)
        yaw = x[2, 0]
        B = np.array([
            [dt * math.cos(yaw), 0.0],
            [dt * math.sin(yaw), 0.0],
            [0.0, dt],
            [1.0, 0.0]
        ], dtype=float)
        x_next = F @ x + B @ u
        x_next[2, 0] = angle_mod(x_next[2, 0])
        return x_next

    def _jacob_f(self, x, u, dt):
        yaw = x[2, 0]
        v_in = u[0, 0]
        return np.array([
            [1.0, 0.0, -dt * v_in * math.sin(yaw), dt * math.cos(yaw)],
            [0.0, 1.0, dt * v_in * math.cos(yaw), dt * math.sin(yaw)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=float)

    def _obs_model(self, x):
        H = np.array([[1, 0, 0, 0],
                      [0, 1, 0, 0],
                      [0, 0, 1, 0]], dtype=float)
        return H @ x, H

    def predict(self, u: np.ndarray, dt: float):
        if not self.initialized:
            return
        x_pred = self._motion_model(self.x, u, dt)
        jF = self._jacob_f(self.x, u, dt)
        P_pred = jF @ self.P @ jF.T + self.Q
        self.x, self.P = x_pred, P_pred

    def update(self, z: np.ndarray):
        if not self.initialized:
            self.x = np.zeros((4, 1))
            self.x[0, 0] = float(z[0, 0])
            self.x[1, 0] = float(z[1, 0])
            self.x[2, 0] = angle_mod(float(z[2, 0]))
            self.x[3, 0] = 0.0
            self.P = np.eye(4)
            self.initialized = True
            return
        z_pred, H = self._obs_model(self.x)
        y = z - z_pred
        y[2, 0] = angle_mod(y[2, 0])
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.x[2, 0] = angle_mod(self.x[2, 0])
        self.P = (np.eye(4) - K @ H) @ self.P


# ============================================================
# D* Lite core
# ============================================================
class GridNode:
    def __init__(self, x: int = 0, y: int = 0, cost: float = 0.0):
        self.x = x
        self.y = y
        self.cost = cost

def add_coordinates(n1: GridNode, n2: GridNode):
    return GridNode(n1.x + n2.x, n1.y + n2.y, n1.cost + n2.cost)

def compare_coordinates(n1: GridNode, n2: GridNode):
    return (n1.x == n2.x) and (n1.y == n2.y)

class DStarLiteCore:
    motions = [
        GridNode(1, 0, 1), GridNode(0, 1, 1), GridNode(-1, 0, 1), GridNode(0, -1, 1),
        GridNode(1, 1, math.sqrt(2)), GridNode(1, -1, math.sqrt(2)),
        GridNode(-1, 1, math.sqrt(2)), GridNode(-1, -1, math.sqrt(2))
    ]

    def __init__(self, ox: list, oy: list):
        self.x_min_world = int(min(ox))
        self.y_min_world = int(min(oy))
        self.x_max = int(abs(max(ox) - self.x_min_world)) + 1
        self.y_max = int(abs(max(oy) - self.y_min_world)) + 1
        self.obstacles = [
            GridNode(x - self.x_min_world, y - self.y_min_world)
            for x, y in zip(ox, oy)
        ]
        self.obstacles_xy = np.array([[ob.x, ob.y] for ob in self.obstacles], dtype=int)
        self.start = GridNode(0, 0)
        self.goal = GridNode(0, 0)
        self.U = []
        self.km = 0.0
        self.kold = (0.0, 0.0)
        self.rhs = self._create_grid(float("inf"))
        self.g = self._create_grid(float("inf"))
        self.detected_obstacles_xy = np.empty((0, 2), dtype=int)
        self.initialized = False
        self.soft_costs: dict[tuple[int, int], float] = {}

    def _create_grid(self, val: float):
        return np.full((self.x_max, self.y_max), val, dtype=float)

    def _is_obstacle(self, n: GridNode):
        x, y = n.x, n.y
        if self.obstacles_xy.shape[0] and (
            self.obstacles_xy[
                (self.obstacles_xy[:, 0] == x) & (self.obstacles_xy[:, 1] == y)
            ].size > 0
        ):
            return True
        if self.detected_obstacles_xy.shape[0] and (
            self.detected_obstacles_xy[
                (self.detected_obstacles_xy[:, 0] == x) & (self.detected_obstacles_xy[:, 1] == y)
            ].size > 0
        ):
            return True
        return False

    def c(self, n1: GridNode, n2: GridNode):
        if self._is_obstacle(n2):
            return math.inf
        d = GridNode(n1.x - n2.x, n1.y - n2.y)
        cand = list(filter(lambda m: compare_coordinates(m, d), self.motions))
        if not cand:
            return math.inf
        base = cand[0].cost
        pen = self.soft_costs.get((n2.x, n2.y), 0.0)
        return base + pen

    def h(self, s: GridNode):
        dx = abs(s.x - self.start.x)
        dy = abs(s.y - self.start.y)
        return (dx + dy) + (math.sqrt(2.0) - 2.0) * min(dx, dy)

    def calculate_key(self, s: GridNode):
        g_rhs = min(self.g[s.x][s.y], self.rhs[s.x][s.y])
        return (g_rhs + self.h(s) + self.km, g_rhs)

    def is_valid(self, n: GridNode):
        return (0 <= n.x < self.x_max) and (0 <= n.y < self.y_max)

    def _neigh(self, u: GridNode):
        return [
            add_coordinates(u, m) for m in self.motions
            if self.is_valid(add_coordinates(u, m))
        ]

    def pred(self, u):
        return self._neigh(u)

    def succ(self, u):
        return self._neigh(u)

    def initialize(self, s_world: GridNode, g_world: GridNode):
        self.start.x = s_world.x - self.x_min_world
        self.start.y = s_world.y - self.y_min_world
        self.goal.x = g_world.x - self.x_min_world
        self.goal.y = g_world.y - self.y_min_world
        if not self.initialized:
            self.initialized = True
        self.U.clear()
        self.km = 0.0
        self.rhs = self._create_grid(math.inf)
        self.g = self._create_grid(math.inf)
        self.rhs[self.goal.x][self.goal.y] = 0.0
        self.U.append((self.goal, self.calculate_key(self.goal)))

    def _remove_from_U(self, u: GridNode):
        if any(compare_coordinates(u, n) for n, _ in self.U):
            self.U = [(n, k) for n, k in self.U if not compare_coordinates(n, u)]
        self.U.sort(key=lambda x: x[1])

    def update_vertex(self, u: GridNode):
        if not compare_coordinates(u, self.goal):
            self.rhs[u.x][u.y] = min(
                [self.c(u, sp) + self.g[sp.x][sp.y] for sp in self.succ(u)] + [math.inf]
            )
        self._remove_from_U(u)
        if self.g[u.x][u.y] != self.rhs[u.x][u.y]:
            self.U.append((u, self.calculate_key(u)))
            self.U.sort(key=lambda x: x[1])

    def _compare_keys(self, k1, k2):
        return (k1[0] < k2[0]) or ((k1[0] == k2[0]) and (k1[1] < k2[1]))

    def _cond(self):
        return (
            len(self.U) > 0
            and self._compare_keys(self.U[0][1], self.calculate_key(self.start))
        ) or (
            self.rhs[self.start.x][self.start.y] != self.g[self.start.x][self.start.y]
        )

    def needs_work(self) -> bool:
        self.U.sort(key=lambda x: x[1])
        return self._cond()

    def compute_shortest_path(self, max_iters=500000):
        self.U.sort(key=lambda x: x[1])
        it = 0
        while self._cond():
            it += 1
            if it > max_iters:
                break
            self.kold = self.U[0][1]
            u = self.U[0][0]
            self.U.pop(0)
            if self._compare_keys(self.kold, self.calculate_key(u)):
                self.U.append((u, self.calculate_key(u)))
                self.U.sort(key=lambda x: x[1])
            elif self.g[u.x, u.y] > self.rhs[u.x, u.y]:
                self.g[u.x, u.y] = self.rhs[u.x, u.y]
                for s in self.pred(u):
                    self.update_vertex(s)
            else:
                self.g[u.x, u.y] = math.inf
                for s in self.pred(u) + [u]:
                    self.update_vertex(s)

    def compute_current_path(self):
        path = []
        cur = GridNode(self.start.x, self.start.y)
        guard = 0
        while not compare_coordinates(cur, self.goal):
            path.append(GridNode(cur.x, cur.y))
            succs = self.succ(cur)
            if not succs:
                break
            cur = min(succs, key=lambda sp: self.c(cur, sp) + self.g[sp.x][sp.y])
            guard += 1
            if guard > (self.x_max * self.y_max):
                break
        path.append(GridNode(self.goal.x, self.goal.y))
        return path


# ============================================================
# D* Lite wrapper
# ============================================================
class DStarLiteWrapper:
    def __init__(self, grid_res=1.0):
        self.grid_res = grid_res
        self.core: Optional[DStarLiteCore] = None
        self._last_start_world_cell = None
        self.prev_soft_map: dict[tuple[int, int], float] = {}

    def compute_some(self, iters: int = 4000):
        if self.core is None:
            return
        self.core.compute_shortest_path(max_iters=iters)

    def needs_work(self) -> bool:
        if self.core is None:
            return False
        return self.core.needs_work()

    def extract_path(self) -> List[Tuple[float, float]]:
        if self.core is None:
            return []
        nodes = self.core.compute_current_path()
        out: List[Tuple[float, float]] = []
        for n in nodes:
            gx_world = n.x + self.core.x_min_world
            gy_world = n.y + self.core.y_min_world
            out.append((gx_world * self.grid_res, gy_world * self.grid_res))
        return out

    def _expand_with_margin(self, cells, start_cell, goal_cell, margin_cells):
        xs = [c[0] for c in cells] + [start_cell[0], goal_cell[0]]
        ys = [c[1] for c in cells] + [start_cell[1], goal_cell[1]]
        xmin = min(xs) - margin_cells
        xmax = max(xs) + margin_cells
        ymin = min(ys) - margin_cells
        ymax = max(ys) + margin_cells
        return xmin, xmax, ymin, ymax

    def initialize(self, start_xy_m, goal_xy_m, static_cells: set, margin_m=60.0):
        start_c = to_grid_cell(start_xy_m)
        goal_c = to_grid_cell(goal_xy_m)
        margin_cells = int(round(margin_m / self.grid_res))
        xmin, xmax, ymin, ymax = self._expand_with_margin(
            list(static_cells), start_c, goal_c, margin_cells
        )
        ox, oy = [], []
        for x in range(xmin, xmax + 1):
            ox += [x, x]
            oy += [ymin, ymax]
        for y in range(ymin, ymax + 1):
            ox += [xmin, xmax]
            oy += [y, y]
        for (gx, gy) in static_cells:
            ox.append(gx)
            oy.append(gy)
        self.core = DStarLiteCore(ox, oy)
        self.core.initialize(GridNode(start_c[0], start_c[1]), GridNode(goal_c[0], goal_c[1]))
        self.core.compute_shortest_path(max_iters=15000)
        self._last_start_world_cell = start_c
        self.prev_soft_map.clear()
        self.core.soft_costs.clear()

    def update_start(self, new_xy_m):
        if self.core is None:
            return False
        new_c = to_grid_cell(new_xy_m)
        cx = clamp(new_c[0], self.core.x_min_world, self.core.x_min_world + self.core.x_max - 1)
        cy = clamp(new_c[1], self.core.y_min_world, self.core.y_min_world + self.core.y_max - 1)
        new_c = (int(cx), int(cy))
        moved = False
        if self._last_start_world_cell is None:
            self._last_start_world_cell = new_c
            moved = True
        dx = abs(new_c[0] - self._last_start_world_cell[0])
        dy = abs(new_c[1] - self._last_start_world_cell[1])
        steps = max(dx, dy)
        if steps > 0:
            self.core.km += float(steps)
            self._last_start_world_cell = new_c
            moved = True
        self.core.start.x = new_c[0] - self.core.x_min_world
        self.core.start.y = new_c[1] - self.core.y_min_world
        return moved

    def update_obstacles(self, changed_cells: list[tuple[tuple[int, int], bool]]):
        if self.core is None:
            return bool(changed_cells)
        anything_changed = False
        for (gx, gy), blocked in changed_cells:
            lx = gx - self.core.x_min_world
            ly = gy - self.core.y_min_world
            if not (0 <= lx < self.core.x_max and 0 <= ly < self.core.y_max):
                continue
            if blocked:
                present_static = (
                    self.core.obstacles_xy[
                        (self.core.obstacles_xy[:, 0] == lx) & (self.core.obstacles_xy[:, 1] == ly)
                    ].size > 0
                )
                present_dynamic = (
                    self.core.detected_obstacles_xy[
                        (self.core.detected_obstacles_xy[:, 0] == lx)
                        & (self.core.detected_obstacles_xy[:, 1] == ly)
                    ].size > 0
                )
                if (not present_static) and (not present_dynamic):
                    if self.core.detected_obstacles_xy.size == 0:
                        self.core.detected_obstacles_xy = np.array([[lx, ly]], dtype=int)
                    else:
                        self.core.detected_obstacles_xy = np.vstack(
                            [self.core.detected_obstacles_xy, [lx, ly]]
                        )
                    anything_changed = True
            else:
                if self.core.detected_obstacles_xy.size > 0:
                    mask = ~(
                        (self.core.detected_obstacles_xy[:, 0] == lx)
                        & (self.core.detected_obstacles_xy[:, 1] == ly)
                    )
                    new_arr = self.core.detected_obstacles_xy[mask]
                    if new_arr.shape[0] != self.core.detected_obstacles_xy.shape[0]:
                        self.core.detected_obstacles_xy = new_arr
                        anything_changed = True
            u = GridNode(lx, ly)
            for s in self.core.pred(u) + [u]:
                self.core.update_vertex(s)
        return anything_changed

    def set_soft_layers(
        self,
        dynamic_cells: set[tuple[int, int]],
        trail_costs: dict[tuple[int, int], float],
        dyn_penalty: float = SOFT_COST_PENALTY,
    ) -> bool:
        if self.core is None:
            return False

        new_map: dict[tuple[int, int], float] = {}

        if dynamic_cells:
            for (gx, gy) in dynamic_cells:
                lx = gx - self.core.x_min_world
                ly = gy - self.core.y_min_world
                if 0 <= lx < self.core.x_max and 0 <= ly < self.core.y_max:
                    new_map[(lx, ly)] = dyn_penalty

        for (gx, gy), pen in (trail_costs or {}).items():
            lx = gx - self.core.x_min_world
            ly = gy - self.core.y_min_world
            if 0 <= lx < self.core.x_max and 0 <= ly < self.core.y_max:
                prev = new_map.get((lx, ly), 0.0)
                new_map[(lx, ly)] = max(prev, float(pen))

        changed = False
        if len(new_map) != len(self.prev_soft_map):
            changed = True
        else:
            for k, v in new_map.items():
                if abs(v - self.prev_soft_map.get(k, -9999.0)) > 1e-6:
                    changed = True
                    break

        if not changed:
            return False

        self.core.soft_costs = new_map.copy()
        to_update = set(new_map.keys()) | set(self.prev_soft_map.keys())
        for (lx, ly) in to_update:
            u = GridNode(lx, ly)
            for s in self.core.pred(u) + [u]:
                self.core.update_vertex(s)
        self.prev_soft_map = new_map
        return True


# ============================================================
# Temporal dynamic occupancy
# ============================================================
class TemporalOcc:
    def __init__(self, k_frames=5, m_confirm=3, inflate=1, release_frames=6):
        self.history = deque(maxlen=k_frames)
        self.k = k_frames
        self.m = m_confirm
        self.inflate = inflate
        self.release = release_frames
        self.frame = 0
        self.last_seen = {}
        self.prev_output = set()

    def update(self, cells_set: set[tuple[int, int]]):
        self.history.append(cells_set)
        self.frame += 1
        for c in cells_set:
            self.last_seen[c] = self.frame

    def current(self) -> set[tuple[int, int]]:
        if not self.history:
            return set()
        counts = defaultdict(int)
        for s in self.history:
            for c in s:
                counts[c] += 1
        confirmed = {c for c, cnt in counts.items() if cnt >= self.m}
        if self.prev_output:
            keep = {
                c
                for c in self.prev_output
                if (self.frame - self.last_seen.get(c, -10**9)) <= self.release
            }
            confirmed |= keep
        self.prev_output = confirmed.copy()
        if self.inflate <= 0:
            return confirmed
        inf = set()
        r = self.inflate
        for (gx, gy) in confirmed:
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    inf.add((gx + dx, gy + dy))
        return inf


# ============================================================
# DWA
# ============================================================
class RobotType(Enum):
    CIRCLE = 0
    RECTANGLE = 1


class DWAConfig:
    def __init__(
        self,
        max_speed: float,
        min_speed: float,
        max_yaw_rate: float,
        max_accel: float,
        max_delta_yaw_rate: float,
        robot_radius: float,
    ):
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.max_yaw_rate = max_yaw_rate
        self.max_accel = max_accel
        self.max_delta_yaw_rate = max_delta_yaw_rate

        self.v_resolution = 0.2  
        self.yaw_rate_resolution = np.deg2rad(4.0)  
        self.dt = 0.1  
        self.predict_time = 2.5  

        self.to_goal_cost_gain = 0.15
        self.speed_cost_gain = 1.0
        self.obstacle_cost_gain = 1.0
        self.robot_stuck_flag_cons = 0.001
        self.robot_type = RobotType.CIRCLE
        self.robot_radius = robot_radius
        self.robot_width = 0.5
        self.robot_length = 1.2


def dwa_motion(x, u, dt):
    x = np.array(x, dtype=float)
    v = u[0]
    omega = u[1]
    x[2] += omega * dt
    x[0] += v * math.cos(x[2]) * dt
    x[1] += v * math.sin(x[2]) * dt
    x[3] = v
    x[4] = omega
    return x


def dwa_calc_dynamic_window(x, config: DWAConfig):
    Vs = [config.min_speed, config.max_speed,
          -config.max_yaw_rate, config.max_yaw_rate]
    Vd = [
        x[3] - config.max_accel * config.dt,
        x[3] + config.max_accel * config.dt,
        x[4] - config.max_delta_yaw_rate * config.dt,
        x[4] + config.max_delta_yaw_rate * config.dt,
    ]
    dw = [
        max(Vs[0], Vd[0]),
        min(Vs[1], Vd[1]),
        max(Vs[2], Vd[2]),
        min(Vs[3], Vd[3]),
    ]
    return dw


def dwa_predict_trajectory(x_init, v, y, config: DWAConfig):
    x = np.array(x_init, dtype=float)
    traj = np.array(x)
    time = 0.0
    while time <= config.predict_time:
        x = dwa_motion(x, [v, y], config.dt)
        traj = np.vstack((traj, x))
        time += config.dt
    return traj


def dwa_calc_obstacle_cost(traj, ob: np.ndarray, config: DWAConfig):
    if ob is None or ob.shape[0] == 0:
        return 0.0
    ox = ob[:, 0]
    oy = ob[:, 1]
    dx = traj[:, 0] - ox[:, None]
    dy = traj[:, 1] - oy[:, None]
    r = np.hypot(dx, dy)
    if config.robot_type == RobotType.CIRCLE:
        if np.array(r <= config.robot_radius).any():
            return float("inf")
    min_r = np.min(r)
    return 1.0 / max(min_r, 1e-6)


def dwa_calc_to_goal_cost(traj, goal):
    dx = goal[0] - traj[-1, 0]
    dy = goal[1] - traj[-1, 1]
    error_angle = math.atan2(dy, dx)
    cost_angle = error_angle - traj[-1, 2]
    cost = abs(math.atan2(math.sin(cost_angle), math.cos(cost_angle)))
    return cost


def dwa_calc_control_and_trajectory(x, dw, config: DWAConfig, goal, ob: np.ndarray):
    x_init = np.array(x, dtype=float)
    min_cost = float("inf")
    best_u = [0.0, 0.0]
    best_traj = np.array([x_init])

    for v in np.arange(dw[0], dw[1] + 1e-6, config.v_resolution):
        for y in np.arange(dw[2], dw[3] + 1e-6, config.yaw_rate_resolution):
            traj = dwa_predict_trajectory(x_init, v, y, config)
            to_goal_cost = config.to_goal_cost_gain * dwa_calc_to_goal_cost(traj, goal)
            speed_cost = config.speed_cost_gain * (config.max_speed - traj[-1, 3])
            ob_cost = config.obstacle_cost_gain * dwa_calc_obstacle_cost(traj, ob, config)
            final_cost = to_goal_cost + speed_cost + ob_cost
            if final_cost < min_cost:
                min_cost = final_cost
                best_u = [v, y]
                best_traj = traj
                if abs(best_u[0]) < config.robot_stuck_flag_cons and abs(x[3]) < config.robot_stuck_flag_cons:
                    best_u[1] = -config.max_delta_yaw_rate
    return best_u, best_traj


def dwa_control(x, config: DWAConfig, goal, ob: np.ndarray):
    dw = dwa_calc_dynamic_window(x, config)
    u, traj = dwa_calc_control_and_trajectory(x, dw, config, goal, ob)
    return u, traj


# ============================================================
# Hybrid Planner Node
# ============================================================
class PathPlanner(RosNode):
    def __init__(self):
        super().__init__('path_planner')

        self._dyn_seen_consec = defaultdict(int)
        self._hard_dyn_cells = set()

        self.create_subscription(SimpleLidar, '/lidar', self.lidar_cb, qos_sensor)
        self.create_subscription(Goal, '/goal', self.goal_cb, qos_profile)
        self.create_subscription(Bool, '/collision', self.collision_cb, qos_profile)
        self.create_subscription(WallList, '/walls', self.walls_cb, qos_profile)
        self.create_subscription(SimpleGPS, '/gps_1', self.gps_cb, qos_profile)
        self.create_subscription(SimpleGPS, '/gps_2', self.gps_cb, qos_profile)

        self.pub_control = self.create_publisher(Control, '/control', qos_profile)

        self.ekf = EKF(Q_DIAG, R_DIAG)

        self.pose = np.array([0.0, 0.0, 0.0])
        self.speed = 0.0
        self.dt = 0.02
        self.prev_t = self.get_clock().now()
        self.prev_yaw = 0.0
        self.goal_xy = None
        self.lidar = None
        self.wall_list = []

        self.WB = 2.5
        self.MAX_STEER = np.deg2rad(45.0)
        self.MAX_SPEED = 20.0 / 3.6
        self.MAX_ACCEL = 0.5
        self.lookahead = LOOKAHEAD_MIN
        self.lookahead_lp = LOOKAHEAD_MIN
        self.max_steer_rate = np.deg2rad(MAX_STEER_RATE_DPS)
        self.prev_steer = 0.0

        self.t_start = self.get_clock().now()
        self.startup_secs = 1.8
        self.start_max_steer_rate = np.deg2rad(28.0)

        self.Kp, self.Ki, self.Kd = 0.5, 0.0, 0.0
        self.I, self.prev_e = 0.0, 0.0

        self.dstar = DStarLiteWrapper(grid_res=GRID_RES)
        self.have_dstar = False
        self.prev_static_cells = set()
        self.global_path: List[Tuple[float, float]] = []
        self.path_cumlen: List[float] = []
        self.s_progress: float = 0.0
        self.plan_pending = False

        self.front_arc = np.deg2rad(FRONT_ARC_DEG)
        self.temporal_onmap = TemporalOcc(
            k_frames=DYN_PERSIST_K,
            m_confirm=DYN_CONFIRM_M,
            inflate=DYN_INFLATE_CELLS,
            release_frames=DYN_RELEASE_FRAMES,
        )
        self.temporal_offmap = TemporalOcc(
            k_frames=OFFMAP_PERSIST_K,
            m_confirm=OFFMAP_CONFIRM_M,
            inflate=OFFMAP_INFLATE_CELLS,
            release_frames=OFFMAP_RELEASE_FRAMES,
        )

        self._frame_dyn_cells_inst: set[tuple[int, int]] = set()
        self._frame_dyn_near: set[tuple[int, int]] = set()
        self.latest_dyn_cells: set[tuple[int, int]] = set()
        self.inst_dyn_cells: set[tuple[int, int]] = set()
        self.lidar_rx_time = self.get_clock().now()
        self.lidar_scan_age = 0.0

        self.mode = 'GLOBAL'
        self.collision_strikes = 0
        self._collision_active = False
        self._last_collision_ts = self.get_clock().now()
        self._last_no_collision_ts = self.get_clock().now()

        self.emergency_active = False
        self.t_emergency_start = self.get_clock().now()

        self.trail_samples: deque[tuple[tuple[int, int], rclpy.time.Time]] = deque(maxlen=2000)
        self._trail_last_xy: Optional[Tuple[float, float]] = None

        max_yaw_rate = np.deg2rad(40.0)
        self.dwa_cfg = DWAConfig(
            max_speed=MAX_TARGET_SPEED,
            min_speed=0.0,
            max_yaw_rate=max_yaw_rate,
            max_accel=self.MAX_ACCEL,
            max_delta_yaw_rate=np.deg2rad(40.0),
            robot_radius=1.0,
        )
        self.dwa_obstacles = np.empty((0, 2), dtype=float)
        self.dwa_last_traj = None
        self.dwa_last_goal = None

        self.control_timer = self.create_timer(0.02, self.control_update)
        self.plan_timer = self.create_timer(0.03, self.plan_update)
        self.viz_timer = self.create_timer(0.25, self.viz_update)

        self.fig, self.ax = plt.subplots()
        self.line_path, = self.ax.plot([], [], 'b-', label='Path (D*/Local)')
        self.me_marker, = self.ax.plot([], [], 'go', label='pose')
        self.tg_marker, = self.ax.plot([], [], 'ro', label='target')
        self.wall_rects: List[Rectangle] = []
        self._walls_hash = None
        self.ax.set_xlim(-20, 100)
        self.ax.set_ylim(-20, 100)
        self.ax.grid()
        self.ax.legend()
        plt.ion()
        plt.show(block=False)

        self.last_target = (0.0, 0.0)
        self.last_tgt_idx = 0

        self._viz_dyn_on = set()
        self._viz_dyn_off = set()

        self.fig_dwa, self.ax_dwa = plt.subplots()
        self.ax_dwa.set_title("DWA Local Planner")
        self.ax_dwa.set_aspect('equal')
        self.ax_dwa.grid(True)
        plt.ion()
        plt.show(block=False)

        self.static_cells = set()
        self.dwa_dyn_cells = set()

    # ---------- Added Missing Method ----------
    def _pick_local_subgoal(self, dist_m: float) -> Tuple[float, float]:
        """
        Finds a point on the global path approximately 'dist_m' meters ahead of the robot.
        If the path is shorter than dist_m, returns the end of the path.
        """
        if not self.global_path:
            return (self.pose[0], self.pose[1])
        
        # 1. Find the closest point index on the path (current progress)
        i, _, _ = self._project_to_polyline(self.pose[0], self.pose[1])
        
        # 2. Iterate forward accumulating distance
        d_acc = 0.0
        goal_pt = self.global_path[-1] # Default to the final goal
        
        for idx in range(i, len(self.global_path) - 1):
            p1 = self.global_path[idx]
            p2 = self.global_path[idx+1]
            seg_len = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            d_acc += seg_len
            if d_acc >= dist_m:
                goal_pt = p2
                break
                
        return goal_pt
    # ------------------------------------------

    def gps_cb(self, msg: SimpleGPS):
        z = np.array([[msg.x], [msg.y], [angle_mod(msg.yaw)]], dtype=float)
        self.ekf.update(z)
        self.pose = np.array(
            [self.ekf.x[0, 0], self.ekf.x[1, 0], self.ekf.x[2, 0]], dtype=float
        )
        self.speed = float(self.ekf.x[3, 0])

    def lidar_cb(self, msg: SimpleLidar):
        now = self.get_clock().now()
        self.lidar_scan_age = (now - self.lidar_rx_time).nanoseconds / 1e9
        self.lidar_rx_time = now
        self.lidar = msg.beams

        if self.lidar is None or len(self.lidar) == 0:
            self.dwa_obstacles = np.empty((0, 2), dtype=float)
            return

        x, y, yaw = self.pose
        N = len(self.lidar)
        inc = 2 * np.pi / N
        cells_inst = set()
        near_cells = set()
        ob_local = []

        for i, r in enumerate(self.lidar):
            if not np.isfinite(r):
                continue
            if r >= LIDAR_MAX - 1e-6:
                continue
            if r <= LIDAR_MIN:
                continue

            rel = angle_mod(i * inc)
            if abs(rel) > self.front_arc:
                continue

            wx = x + r * math.cos(yaw + rel)
            wy = y + r * math.sin(yaw + rel)
            cell = (int(round(wx / GRID_RES)), int(round(wy / GRID_RES)))
            cells_inst.add(cell)

            if r < FAST_ADD_DIST:
                cx, cy = cell
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        near_cells.add((cx + dx, cy + dy))

            lx = r * math.cos(rel)
            ly = r * math.sin(rel)
            ob_local.append((lx, ly))

        self._frame_dyn_cells_inst = cells_inst
        self._frame_dyn_near = near_cells
        self.inst_dyn_cells = cells_inst | near_cells

        if ob_local:
            self.dwa_obstacles = np.array(ob_local, dtype=float)
        else:
            self.dwa_obstacles = np.empty((0, 2), dtype=float)

        self.plan_pending = True

    def goal_cb(self, msg: Goal):
        self.goal_xy = (msg.x, msg.y)
        self.have_dstar = False
        self.plan_pending = True

    def collision_cb(self, msg: Bool):
        now = self.get_clock().now()
        if msg.data:
            dt = (now - self._last_collision_ts).nanoseconds / 1e9
            if (not self._collision_active) or (dt >= COLLISION_COOLDOWN_SEC):
                self.collision_strikes += 1
            self._last_collision_ts = now
            self._collision_active = True
            self.get_logger().warn(f"[COLLISION] strikes={self.collision_strikes}")

            if self.collision_strikes >= EMERGENCY_STRIKE_LIMIT and not self.emergency_active:
                self.emergency_active = True
                self.t_emergency_start = now
                self.mode = 'GLOBAL'
                self.have_dstar = False
                self.plan_pending = True
                self.get_logger().error(
                    ">>> EMERGENCY STOP: Using current LiDAR as hard obstacles, forcing D* replanning."
                )
                return
            if (
                self.collision_strikes >= COLLISION_STRIKE_LIMIT
                and self.mode != 'LOCAL_ONLY'
                and not self.emergency_active
            ):
                self.mode = 'LOCAL_ONLY'
                self.have_dstar = False
                self.plan_pending = True
                self.get_logger().error(
                    ">>> Switching to LOCAL_ONLY mode due to repeated collisions."
                )
        else:
            self._collision_active = False
            self._last_no_collision_ts = now

        if self.mode == 'GLOBAL' and not self.emergency_active:
            self.have_dstar = False
            self.plan_pending = True

    def walls_cb(self, msg: WallList):
        self.wall_list = [
            (w.bl_x, w.bl_y, w.size_x, w.size_y) for w in msg.walls
        ]
        self.plan_pending = True
        self._walls_hash = None

    def _dynamic_cells_masked(self, dyn_union: Set[tuple]) -> Set[tuple]:
        if not self.goal_xy or not dyn_union:
            return dyn_union
        gx, gy = to_grid_cell(self.goal_xy)
        r = GOAL_MASK_R_CELLS
        return {
            c for c in dyn_union if not (max(abs(c[0] - gx), abs(c[1] - gy)) <= r)
        }

    def _update_and_build_trail_costs(
        self, now: rclpy.time.Time
    ) -> dict[tuple[int, int], float]:
        cur_xy = (float(self.pose[0]), float(self.pose[1]))
        if self._trail_last_xy is None:
            self._trail_last_xy = cur_xy
        moved = math.hypot(
            cur_xy[0] - self._trail_last_xy[0], cur_xy[1] - self._trail_last_xy[1]
        )
        if moved >= BACKTRACK_SAMPLE_DIST_M:
            cell = to_grid_cell(cur_xy)
            if (not self.trail_samples) or (self.trail_samples[-1][0] != cell):
                self.trail_samples.append((cell, now))
                self._trail_last_xy = cur_xy

        while self.trail_samples and (
            (now - self.trail_samples[0][1]).nanoseconds / 1e9
            > BACKTRACK_TRAIL_HORIZON_SEC
        ):
            self.trail_samples.popleft()

        trail_costs: dict[tuple[int, int], float] = {}
        if not self.trail_samples:
            return trail_costs

        effective_list = (
            list(self.trail_samples)[:-BACKTRACK_EXCLUDE_RECENT]
            if len(self.trail_samples) > BACKTRACK_EXCLUDE_RECENT
            else []
        )
        for (cell, ts) in effective_list:
            age = (now - ts).nanoseconds / 1e9
            w = BACKTRACK_PENALTY_MAX * math.exp(
                -max(0.0, age) / max(1e-6, BACKTRACK_PENALTY_DECAY_SEC)
            )
            trail_costs[cell] = max(trail_costs.get(cell, 0.0), w)
        return trail_costs

    def plan_update(self):
        now = self.get_clock().now()

        raw_static = set()
        for bx, by, sx, sy in self.wall_list:
            x0 = int(math.floor(bx / GRID_RES))
            x1 = int(math.ceil((bx + sx) / GRID_RES)) - 1
            y0 = int(math.floor(by / GRID_RES))
            y1 = int(math.ceil((by + sy) / GRID_RES)) - 1
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    raw_static.add((gx, gy))
        persisted_raw = raw_static
        static = inflate_cells(persisted_raw, INFLATE_CELLS)
        self.static_cells = static

        if self.goal_xy is None:
            return

        inst_all = (self._frame_dyn_cells_inst | self._frame_dyn_near)
        on_map_now = {c for c in inst_all if c in persisted_raw}
        off_map_now = inst_all - on_map_now

        self.temporal_onmap.update(on_map_now)
        self.temporal_offmap.update(off_map_now)

        dyn_on = self.temporal_onmap.current()
        dyn_off = self.temporal_offmap.current()

        dyn_union = dyn_on | dyn_off
        dyn_masked = self._dynamic_cells_masked(dyn_union)
        self.dwa_dyn_cells = dyn_masked

        self._viz_dyn_on = set(dyn_on)
        self._viz_dyn_off = set(dyn_off)

        if dyn_union != self.latest_dyn_cells:
            self.latest_dyn_cells = dyn_union
            self.plan_pending = True

        trail_costs = self._update_and_build_trail_costs(now)

        if self.emergency_active:
            if not self.have_dstar:
                self.dstar.initialize(tuple(self.pose[:2]), self.goal_xy, static, margin_m=MARGIN_METERS)
                self.have_dstar = True
            base_dyn = self.inst_dyn_cells if self.inst_dyn_cells else dyn_masked
            hard_target = inflate_cells(
                base_dyn, max(DYN_HARD_INFLATE_CELLS, EMERGENCY_INFLATE_CELLS)
            )
            to_add = hard_target - self._hard_dyn_cells
            to_remove = self._hard_dyn_cells - hard_target
            if to_add or to_remove:
                changes2 = [(c, True) for c in to_add] + [(c, False) for c in to_remove]
                self.dstar.update_obstacles(changes2)
                self._hard_dyn_cells = (self._hard_dyn_cells - to_remove) | to_add
            self.dstar.compute_some(iters=EMERGENCY_REPLAN_ITERS)
            if not self.dstar.needs_work():
                self.global_path = self.dstar.extract_path()
                self._build_path_arclen_cache()
                self.s_progress = self._current_s_projection()
            self.plan_pending = False
            t_hold = (now - self.t_emergency_start).nanoseconds / 1e9
            if (self.speed < 0.15) and (t_hold >= EMERGENCY_MIN_HOLD_SEC):
                self.emergency_active = False
                self.collision_strikes = 0
                self.get_logger().info(
                    "EMERGENCY cleared: Resuming GLOBAL D* with new plan."
                )
            return

        if self.mode == 'LOCAL_ONLY':
            self.global_path = self._local_plan_forward()
            self._build_path_arclen_cache()
            self.s_progress = self._current_s_projection()
            self.plan_pending = False
            t_no_col = (now - self._last_no_collision_ts).nanoseconds / 1e9
            if (
                t_no_col >= LOCAL_ONLY_RECOVER_SEC
                and self._front_min_distance() >= FRONT_CLEAR_FOR_RECOVER
            ):
                self.get_logger().info(
                    "LOCAL_ONLY -> GLOBAL candidate: clear for a while. Re-enabling D*."
                )
                self.mode = 'GLOBAL'
                self.collision_strikes = 0
                self.have_dstar = False
                self.plan_pending = True
            return

        if not self.have_dstar:
            self.dstar.initialize(tuple(self.pose[:2]), self.goal_xy, static, margin_m=MARGIN_METERS)
            self.have_dstar = True
            self.plan_pending = True

        moved = self.dstar.update_start(tuple(self.pose[:2]))

        changes = []
        add_s = static - self.prev_static_cells
        rem_s = self.prev_static_cells - static
        if add_s:
            changes += [(c, True) for c in add_s]
        if rem_s:
            changes += [(c, False) for c in rem_s]
        any_hard_changed = self.dstar.update_obstacles(changes)
        self.prev_static_cells = static

        soft_changed = self.dstar.set_soft_layers(dyn_masked, trail_costs, dyn_penalty=SOFT_COST_PENALTY)

        HARD_T_FRAMES = max(3, int(DYN_HARDIFY_SEC / 0.03))
        for c in list(self._dyn_seen_consec.keys()):
            if c not in dyn_masked:
                self._dyn_seen_consec[c] = max(
                    0, self._dyn_seen_consec[c] - DYN_HARD_DECAY_STEPS
                )
                if self._dyn_seen_consec[c] == 0:
                    self._dyn_seen_consec.pop(c, None)
        for c in dyn_masked:
            self._dyn_seen_consec[c] = min(self._dyn_seen_consec.get(c, 0) + 1, 1000)
        promoted = {c for c, n in self._dyn_seen_consec.items() if n >= HARD_T_FRAMES}
        hard_target = inflate_cells(promoted, DYN_HARD_INFLATE_CELLS)
        to_add = hard_target - self._hard_dyn_cells
        to_remove = self._hard_dyn_cells - hard_target
        if to_add or to_remove:
            changes2 = [(c, True) for c in to_add] + [(c, False) for c in to_remove]
            any_hard_dyn_changed = self.dstar.update_obstacles(changes2)
            if any_hard_dyn_changed:
                self.plan_pending = True
            self._hard_dyn_cells = (self._hard_dyn_cells - to_remove) | to_add

        if any_hard_changed or moved or soft_changed or self.plan_pending:
            self.dstar.compute_some(iters=4000)
            if (now - self.t_start).nanoseconds / 1e9 < 1.5 and self.dstar.needs_work():
                self.dstar.compute_some(iters=6000)
            if not self.dstar.needs_work():
                self.global_path = self.dstar.extract_path()
                self._build_path_arclen_cache()
                self.s_progress = self._current_s_projection()
                self.plan_pending = False

    def control_update(self):
        now = self.get_clock().now()
        self.dt = (now - self.prev_t).nanoseconds / 1e9
        if self.dt <= 0.0:
            self.dt = 0.02
        self.prev_t = now

        v_in = float(self.speed)
        yawrate_in = v_in / self.WB * math.tan(self.prev_steer) if self.WB > 1e-6 else 0.0
        self.ekf.predict(np.array([[v_in], [yawrate_in]], dtype=float), self.dt)
        if self.ekf.initialized:
            self.pose = np.array(
                [self.ekf.x[0, 0], self.ekf.x[1, 0], self.ekf.x[2, 0]], dtype=float
            )
            self.speed = float(self.ekf.x[3, 0])

        if self.emergency_active:
            accel = -self.MAX_ACCEL
            steer = clamp(self.prev_steer, -self.MAX_STEER, self.MAX_STEER)
            msg = Control()
            msg.accel = float(accel)
            msg.steering = float(steer)
            self.pub_control.publish(msg)
            return

        if not self.global_path:
            return

        elapsed = (now - self.t_start).nanoseconds / 1e9
        ramp = clamp(elapsed / self.startup_secs, 0.0, 1.0)

        Ld_target = clamp(
            LOOKAHEAD_MIN + TIME_HEADWAY_SEC * self.speed,
            LOOKAHEAD_MIN,
            LOOKAHEAD_MAX,
        )
        alpha_lp = 1.0 - math.exp(-self.dt / max(LD_SMOOTH_TAU, 1e-3))
        self.lookahead_lp += alpha_lp * (Ld_target - self.lookahead_lp)
        Ld = self.lookahead_lp

        target, tgt_idx = self._advance_progress_and_pick_target(Ld)
        self.last_target = target
        self.last_tgt_idx = tgt_idx

        alpha = angle_mod(
            math.atan2(target[1] - self.pose[1], target[0] - self.pose[0])
            - self.pose[2]
        )
        delta_pp = math.atan2(2.0 * self.WB * math.sin(alpha), Ld)

        e_ct, _ = self._crosstrack_error_and_heading()
        e_ct_clamped = clamp(e_ct, -2.0, 2.0)
        w_st = clamp((self.speed - 0.6) / 1.4, 0.0, 1.0)
        delta_st_raw = math.atan2(
            STANLEY_CTE_GAIN * e_ct_clamped, self.speed + STANLEY_V_EPS
        )
        delta_st = w_st * delta_st_raw

        kappa_ff = self._estimate_path_curvature(tgt_idx)
        delta_ff = clamp(
            math.atan(self.WB * kappa_ff), -self.MAX_STEER, self.MAX_STEER
        )

        steer_cmd = angle_mod(delta_pp + STANLEY_BLEND * delta_st + 0.35 * delta_ff)

        yawrate_meas = angle_mod(self.pose[2] - self.prev_yaw) / max(self.dt, 1e-3)
        self.prev_yaw = self.pose[2]
        steer_cmd += -YAW_DAMP_K * yawrate_meas

        steer_cmd = clamp(steer_cmd, -self.MAX_STEER, self.MAX_STEER)
        sched_rate = (1.0 - ramp) * self.start_max_steer_rate + ramp * self.max_steer_rate
        max_d = sched_rate * self.dt
        steer_rl = clamp(steer_cmd, self.prev_steer - max_d, self.prev_steer + max_d)
        tau = 0.22 + 0.12 * (1.0 - ramp)
        alpha_f = 1.0 - math.exp(-self.dt / max(tau, 1e-3))
        steer = self.prev_steer + alpha_f * (steer_rl - self.prev_steer)
        self.prev_steer = steer

        v_ref_dwa = None
        if self.goal_xy is not None and self.dwa_cfg is not None:
            try:
                dwa_goal_world = self._pick_local_subgoal(10.0)
                dx = dwa_goal_world[0] - self.pose[0]
                dy = dwa_goal_world[1] - self.pose[1]
                yaw = self.pose[2]

                gx = math.cos(-yaw) * dx - math.sin(-yaw) * dy
                gy = math.sin(-yaw) * dx + math.cos(-yaw) * dy
                dwa_goal_local = (gx, gy)

                x_dwa = np.array(
                    [0.0, 0.0, 0.0, self.speed, 0.0],
                    dtype=float,
                )
                ob = self.dwa_obstacles
                if ob is None:
                    ob = np.empty((0, 2), dtype=float)

                u_dwa, traj_dwa = dwa_control(x_dwa, self.dwa_cfg, np.array(dwa_goal_local), ob)
                v_ref_dwa = max(0.0, float(u_dwa[0]))
                self.dwa_last_traj = traj_dwa
                self.dwa_last_goal = dwa_goal_local
                self._update_dwa_viz(traj_dwa, ob, dwa_goal_local)
            except Exception as e:
                self.get_logger().warn(f"DWA failed: {e}")

        v_ref = min(self.MAX_SPEED, MAX_TARGET_SPEED)
        d_front = self._front_min_distance()
        if d_front < FRONT_STOP_HARD:
            v_ref = 0.0
        elif d_front < FRONT_STOP_SOFT:
            v_ref = min(v_ref, 3.0 / 3.6)

        kappa = self._estimate_path_curvature(tgt_idx)
        if kappa > 1e-6:
            v_curve = math.sqrt(LATERAL_ACC_MAX / max(kappa, 1e-6))
            v_ref = min(v_ref, v_curve)

        if v_ref_dwa is not None:
            v_ref = min(v_ref, v_ref_dwa)

        e = v_ref - self.speed
        self.I = clamp(self.I + e * self.dt, -10.0, 10.0)
        d = (e - self.prev_e) / max(self.dt, 1e-3)
        accel = clamp(
            self.Kp * e + self.Ki * self.I + self.Kd * d,
            -self.MAX_ACCEL,
            self.MAX_ACCEL,
        )
        self.prev_e = e

        msg = Control()
        msg.accel = float(accel)
        msg.steering = float(steer)
        self.pub_control.publish(msg)

        if int(now.nanoseconds * 1e-9 * 10) % 10 == 0:
            self.get_logger().info(
                f"[{self.mode}] v={self.speed:.2f} v_ref={v_ref:.2f} "
                f"a={accel:.2f} steer={steer:.2f} dF={d_front:.2f} "
                f"Ld={Ld:.2f} kappa={kappa:.4f}"
            )

    def _update_dwa_viz(self, traj: np.ndarray, ob: np.ndarray, goal: Tuple[float, float]):
        if traj is None or traj.shape[0] == 0:
            return
        try:
            self.ax_dwa.cla()
            self.ax_dwa.set_title("DWA Local Planner")
            self.ax_dwa.set_aspect('equal')
            self.ax_dwa.grid(True)
            if ob is not None and ob.shape[0] > 0:
                self.ax_dwa.plot(ob[:, 0], ob[:, 1], ".k", markersize=3)
            self.ax_dwa.plot(traj[:, 0], traj[:, 1], "-r", linewidth=2)
            self.ax_dwa.plot(0.0, 0.0, "ob")
            if goal is not None:
                self.ax_dwa.plot(goal[0], goal[1], "xb")
            self.ax_dwa.set_xlim(-20.0, 20.0)
            self.ax_dwa.set_ylim(-20.0, 20.0)
            self.fig_dwa.canvas.draw()
            self.fig_dwa.canvas.flush_events()
        except Exception:
            pass

    def _refresh_wall_patches(self):
        for p in self.wall_rects:
            try:
                p.remove()
            except Exception:
                pass
        self.wall_rects.clear()
        for bx, by, sx, sy in self.wall_list:
            rect = Rectangle(
                (bx, by),
                sx,
                sy,
                facecolor=VIZ_WALL_FACE,
                edgecolor=VIZ_WALL_EDGE,
                alpha=0.6,
                linewidth=1.0,
            )
            self.ax.add_patch(rect)
            self.wall_rects.append(rect)

    def viz_update(self):
        try:
            new_hash = hash(tuple(tuple(w) for w in self.wall_list))
        except Exception:
            new_hash = None
        if new_hash != self._walls_hash:
            self._refresh_wall_patches()
            self._walls_hash = new_hash

        if self.global_path:
            xs = [p[0] for p in self.global_path]
            ys = [p[1] for p in self.global_path]
            self.line_path.set_data(xs, ys)
        self.me_marker.set_data([self.pose[0]], [self.pose[1]])
        self.tg_marker.set_data([self.last_target[0]], [self.last_target[1]])
        try:
            self.ax.relim()
            self.ax.autoscale_view()
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception:
            pass

    def _local_plan_forward(self) -> List[Tuple[float, float]]:
        x, y, yaw = float(self.pose[0]), float(self.pose[1]), float(self.pose[2])
        d1 = 4.0
        d2 = 8.0
        p1 = (x + d1 * math.cos(yaw), y + d1 * math.sin(yaw))
        p2 = (x + d2 * math.cos(yaw), y + d2 * math.sin(yaw))
        return [(x, y), p1, p2]

    def _build_path_arclen_cache(self):
        self.path_cumlen = [0.0]
        if not self.global_path:
            return
        for i in range(1, len(self.global_path)):
            p0 = self.global_path[i - 1]
            p1 = self.global_path[i]
            ds = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            self.path_cumlen.append(self.path_cumlen[-1] + ds)

    def _project_to_polyline(
        self, x: float, y: float
    ) -> Tuple[int, float, np.ndarray]:
        if len(self.global_path) < 2:
            if self.global_path:
                return 0, 0.0, np.array(self.global_path[0])
            return 0, 0.0, np.array([x, y])

        p = np.array([x, y])
        best_d2 = 1e18
        best_i = 0
        best_t = 0.0
        best_proj = np.array(self.global_path[0])

        for i in range(len(self.global_path) - 1):
            a = np.array(self.global_path[i])
            b = np.array(self.global_path[i + 1])
            v = b - a
            L2 = float(np.dot(v, v))
            if L2 < 1e-12:
                t = 0.0
                proj = a
            else:
                t = float(np.clip(np.dot(p - a, v) / L2, 0.0, 1.0))
                proj = a + t * v
            d2 = float(np.dot(p - proj, p - proj))
            if d2 < best_d2:
                best_d2 = d2
                best_i = i
                best_t = t
                best_proj = proj
        return best_i, best_t, best_proj

    def _current_s_projection(self) -> float:
        if not self.global_path:
            return 0.0
        i, t, proj = self._project_to_polyline(self.pose[0], self.pose[1])
        if not self.path_cumlen or len(self.path_cumlen) != len(self.global_path):
            self._build_path_arclen_cache()
        a = np.array(self.global_path[i])
        if i + 1 < len(self.global_path):
            b = np.array(self.global_path[i + 1])
        else:
            b = a
        segL = float(np.linalg.norm(b - a))
        return self.path_cumlen[i] + t * segL

    def _advance_progress_and_pick_target(
        self, Ld: float
    ) -> Tuple[Tuple[float, float], int]:
        if not self.global_path:
            return (self.pose[0], self.pose[1]), 0
        if not self.path_cumlen or len(self.path_cumlen) != len(self.global_path):
            self._build_path_arclen_cache()
        s_proj = self._current_s_projection()
        self.s_progress = max(s_proj, self.s_progress - 1.0)
        s_tgt = min(self.path_cumlen[-1], self.s_progress + Ld)
        self.s_progress = max(self.s_progress, s_proj)
        j = int(np.searchsorted(self.path_cumlen, s_tgt, side='right') - 1)
        j = int(clamp(j, 0, len(self.global_path) - 2))
        sj = self.path_cumlen[j]
        sj1 = self.path_cumlen[j + 1]
        ratio = (s_tgt - sj) / max(sj1 - sj, 1e-9)
        Pj = np.array(self.global_path[j])
        Pj1 = np.array(self.global_path[j + 1])
        tgt = Pj + ratio * (Pj1 - Pj)
        return (float(tgt[0]), float(tgt[1])), j

    def _crosstrack_error_and_heading(self) -> Tuple[float, float]:
        if len(self.global_path) < 2:
            return 0.0, self.pose[2]
        i, t, proj = self._project_to_polyline(self.pose[0], self.pose[1])
        a = np.array(self.global_path[i])
        if i + 1 < len(self.global_path):
            b = np.array(self.global_path[i + 1])
        else:
            b = a + np.array([1.0, 0.0])
        v = b - a
        L = float(np.linalg.norm(v))
        if L < 1e-9:
            return 0.0, self.pose[2]
        v_unit = v / L
        e_vec = np.array([self.pose[0], self.pose[1]]) - proj
        cross_z = v_unit[0] * e_vec[1] - v_unit[1] * e_vec[0]
        heading = math.atan2(v_unit[1], v_unit[0])
        return cross_z, heading

    def _front_min_distance(self):
        if self.lidar is None or len(self.lidar) == 0:
            return 9e9
        N = len(self.lidar)
        inc = 2 * np.pi / N
        dmin = 9e9
        limit = np.deg2rad(FRONT_STOP_DEG)
        for i, r in enumerate(self.lidar):
            if not np.isfinite(r):
                continue
            if r >= LIDAR_MAX - 1e-6:
                continue
            if r <= LIDAR_MIN:
                continue
            rel = angle_mod(i * inc)
            if abs(rel) <= limit:
                dmin = min(dmin, r)
        return dmin

    def _estimate_path_curvature(self, idx):
        if len(self.global_path) < 3:
            return 0.0
        i0 = max(0, idx - 1)
        i1 = idx
        i2 = min(len(self.global_path) - 1, idx + 1)
        x0, y0 = self.global_path[i0]
        x1, y1 = self.global_path[i1]
        x2, y2 = self.global_path[i2]
        a = math.hypot(x1 - x0, y1 - y0)
        b = math.hypot(x2 - x1, y2 - y1)
        c = math.hypot(x2 - x0, y2 - y0)
        denom = a * b * c
        if denom < 1e-6:
            return 0.0
        area2 = abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0))
        kappa = area2 / denom * 2.0
        return kappa


def main(args=None):
    rclpy.init(args=args)
    node = PathPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard Interrupt (SIGINT)')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()