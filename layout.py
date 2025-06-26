# layout.py (修改版)

import random
import math

class Pin:
    """代表一個引腳，包含其全域 ID 和相對位置"""
    def __init__(self, pin_id, parent_rect, rel_pos):
        self.id = pin_id
        self.parent_rect = parent_rect
        self.rel_pos = rel_pos # (x, y) 相對於父元件中心

    def get_absolute_pos(self):
        """計算並返回引腳在畫布上的絕對座標"""
        return (self.parent_rect.x + self.rel_pos[0], 
                self.parent_rect.y + self.rel_pos[1])

class Rectangle:
    """代表一個元件（矩形）"""
    def __init__(self, rect_id, x, y, w, h, growth_prob=0.5):
        self.id = rect_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.growth_prob = growth_prob
        self.pins = [] # 現在儲存 Pin 物件

    def intersects(self, other):
        """檢查此矩形是否與另一個矩形相交"""
        return not (self.x + self.w / 2 < other.x - other.w / 2 or
                    self.x - self.w / 2 > other.x + other.w / 2 or
                    self.y + self.h / 2 < other.y - other.h / 2 or
                    self.y - self.h / 2 > other.y + other.h / 2)

    def get_bounds(self):
        """取得左上角座標及寬高，方便繪圖"""
        return (self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)

    def is_point_inside(self, px, py):
        """檢查一個點是否在此矩形內部"""
        return (px >= self.x - self.w/2 and px <= self.x + self.w/2 and
                py >= self.y - self.h/2 and py <= self.y + self.h/2)

class Layout:
    """代表一個完整的佈局，包含所有元件、引腳和連線"""
    def __init__(self, width, height):
        self.canvas_width = width
        self.canvas_height = height
        self.rectangles = []
        self.edges = [] # <<< NEW: 新增一個列表來儲存連線

    def add_rectangle(self, rect):
        """新增一個元件到佈局中"""
        self.rectangles.append(rect)

    def get_density(self):
        """計算當前佈局的填充密度"""
        total_area = sum(r.w * r.h for r in self.rectangles)
        return total_area / (self.canvas_width * self.canvas_height)

    def generate_pins(self, k, p):
        """為佈局中所有元件生成引腳"""
        print("\n開始為元件生成引腳...")
        pin_global_id = 0
        for r in self.rectangles:
            area = r.w * r.h
            num_pins = int(k * (area ** p))
            if area > 1 and num_pins == 0: num_pins = 1
            
            r.pins = []
            for _ in range(num_pins):
                pin_x_rel = random.uniform(-r.w / 2, r.w / 2)
                pin_y_rel = random.uniform(-r.h / 2, r.h / 2)
                r.pins.append(Pin(pin_global_id, r, (pin_x_rel, pin_y_rel))) # <<< MODIFIED
                pin_global_id += 1
        print(f"引腳生成完畢，總共生成了 {pin_global_id} 個引腳。")
    
    def generate_edges(self, p_max, decay_rate, max_length_limit): # <<< MODIFIED: 增加 max_length_limit 參數
        """
        生成引腳之間的連線
        p_max: 最大連接機率
        decay_rate: 隨距離的衰減率
        max_length_limit: 連線的最大長度上限
        """
        print("\n開始生成引腳之間的連線...")
        all_pins = [pin for r in self.rectangles for pin in r.pins]
        self.edges = []
        
        # 遍歷所有獨特的引腳對 O(N^2)
        for i in range(len(all_pins)):
            for j in range(i + 1, len(all_pins)):
                pin1 = all_pins[i]
                pin2 = all_pins[j]

                # 確保引腳在不同的元件上
                if pin1.parent_rect.id == pin2.parent_rect.id:
                    continue

                # 計算 L1 曼哈頓距離
                pos1 = pin1.get_absolute_pos()
                pos2 = pin2.get_absolute_pos()
                distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

                # <<< NEW: 過長截斷檢查
                if distance > max_length_limit:
                    continue # 如果超過長度上限，直接跳過

                # 計算連接機率
                prob = p_max * math.exp(-decay_rate * distance)

                # 抽樣決定是否連線
                if random.random() < prob:
                    self.edges.append((pin1, pin2))
        
        print(f"連線生成完畢，總共生成了 {len(self.edges)} 條連線。")