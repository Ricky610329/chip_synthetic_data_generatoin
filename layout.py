# layout.py

import random
import math

class Pin:
    def __init__(self, pin_id, parent_rect, rel_pos):
        self.id, self.parent_rect, self.rel_pos = pin_id, parent_rect, rel_pos
    def get_absolute_pos(self):
        return (self.parent_rect.x + self.rel_pos[0], self.parent_rect.y + self.rel_pos[1])

class Rectangle:
    def __init__(self, rect_id, x, y, w, h, growth_prob=0.5, component_type=None):
        self.id, self.x, self.y, self.w, self.h = rect_id, x, y, w, h
        self.growth_prob, self.component_type = growth_prob, component_type
        self.pins, self.fixed, self.constraints = [], False, {}
    def intersects(self, other):
        return not (self.x + self.w / 2 < other.x - other.w / 2 or self.x - self.w / 2 > other.x + other.w / 2 or
                    self.y + self.h / 2 < other.y - other.h / 2 or self.y - self.h / 2 > other.y + other.h / 2)
    def get_bounds(self):
        return (self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)
    def is_point_inside(self, px, py):
        return (self.x - self.w / 2 <= px <= self.x + self.w / 2 and
                self.y - self.h / 2 <= py <= self.y + self.h / 2)

class Layout:
    def __init__(self, width, height):
        self.canvas_width, self.canvas_height = width, height
        self.rectangles, self.edges = [], []
        self.alignment_constraints, self.hierarchical_group_constraints = [], []

    def get_density(self):
        return sum(r.w * r.h for r in self.rectangles) / (self.canvas_width * self.canvas_height)

    def generate_pins(self, k, p, start_pin_id=0, pin_edge_margin_ratio=0.1):
        print(f"\n為剩餘元件生成引腳 (k={k:.3f}, p={p:.3f})...")
        pin_global_id = start_pin_id
        new_pins_count = 0
        for r in self.rectangles:
            if r.pins: continue
            area = r.w * r.h
            num_pins = int(k * (area ** p))
            if area > 1 and num_pins == 0: num_pins = 1
            if num_pins == 0: continue
            hw, hh = r.w / 2, r.h / 2
            margin_x, margin_y = min(r.w * pin_edge_margin_ratio, hw), min(r.h * pin_edge_margin_ratio, hh)
            for _ in range(num_pins):
                edge = random.choice(['top', 'bottom', 'left', 'right'])
                if edge == 'top': px, py = random.uniform(-hw, hw), random.uniform(-hh, -hh + margin_y)
                elif edge == 'bottom': px, py = random.uniform(-hw, hw), random.uniform(hh - margin_y, hh)
                elif edge == 'left': px, py = random.uniform(-hw, -hw + margin_x), random.uniform(-hh, hh)
                else: px, py = random.uniform(hw - margin_x, hw), random.uniform(-hh, hh)
                r.pins.append(Pin(pin_global_id, r, (px, py)))
                pin_global_id += 1
                new_pins_count += 1
        print(f"為剩餘元件生成了 {new_pins_count} 個新引腳。")

    def generate_edges(self, p_max, decay_rate, max_length_limit, k_neighbors):
        """採用兩階段+K最近鄰策略生成引腳之間的連線。"""
        print(f"\n開始生成 Netlist 連線 (K={k_neighbors})...")
        all_pins = [pin for r in self.rectangles for pin in r.pins]
        if len(all_pins) < 2:
            self.edges = []
            return

        edge_set = set()
        print("  - 階段 1: 最近鄰連接...")
        for i, pin1 in enumerate(all_pins):
            min_dist, nearest_pin = float('inf'), None
            for j, pin2 in enumerate(all_pins):
                if i == j or pin1.parent_rect.id == pin2.parent_rect.id: continue
                pos1, pos2 = pin1.get_absolute_pos(), pin2.get_absolute_pos()
                distance = math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])
                if distance < min_dist:
                    min_dist, nearest_pin = distance, pin2
            if nearest_pin:
                edge_set.add(tuple(sorted((pin1.id, nearest_pin.id))))

        initial_edge_count = len(edge_set)
        print(f"  - 階段 1 完成，生成了 {initial_edge_count} 條基礎連線。")
        
        print(f"  - 階段 2: K-最近鄰機率性連接 (K={k_neighbors})...")
        for pin1 in all_pins:
            neighbors = []
            for pin2 in all_pins:
                if pin1.id == pin2.id or pin1.parent_rect.id == pin2.parent_rect.id:
                    continue
                pos1 = pin1.get_absolute_pos()
                pos2 = pin2.get_absolute_pos()
                distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
                if distance < max_length_limit:
                    neighbors.append((distance, pin2))
            
            neighbors.sort(key=lambda x: x[0])
            
            for dist, pin2 in neighbors[:k_neighbors]:
                prob = p_max * math.exp(-decay_rate * dist)
                if random.random() < prob:
                    edge_set.add(tuple(sorted((pin1.id, pin2.id))))

        self.edges = list(edge_set)
        print(f"  - 階段 2 完成，新增了 {len(self.edges) - initial_edge_count} 條增補連線。")
        print(f"Netlist 生成完畢，總共 {len(self.edges)} 條連線。")