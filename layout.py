# layout.py (已更新，增加約束儲存)

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
        self.x = x; self.y = y; self.w = w; self.h = h
        self.growth_prob = growth_prob
        self.pins = [] # 現在儲存 Pin 物件
        self.fixed = False
        self.group_id = None
        self.group_type = None

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
        self.canvas_width = width; self.canvas_height = height
        self.rectangles = []
        self.edges = [] # 儲存 netlist 連線 (pin_id, pin_id)
        
        # ✨ 新增: 專門儲存不同類型的約束
        self.alignment_constraints = [] # 儲存 e.g., (rect_id1, rect_id2, 'left')
        self.hierarchical_group_constraints = [] # 儲存 e.g., [rect_id1, rect_id2, rect_id3]

    def add_rectangle(self, rect):
        self.rectangles.append(rect)

    def get_density(self):
        total_area = sum(r.w * r.h for r in self.rectangles)
        return total_area / (self.canvas_width * self.canvas_height)

    def generate_pins(self, k, p, start_pin_id=0):
        """為佈局中【非固定】的元件生成引腳"""
        print("\n開始為【非固定】元件生成引腳...")
        pin_global_id = start_pin_id
        new_pins_count = 0
        for r in self.rectangles:
            if r.fixed: # 對稱和對齊元件通常是固定的
                continue
            
            area = r.w * r.h
            num_pins = int(k * (area ** p))
            if area > 1 and num_pins == 0: num_pins = 1
            
            r.pins = [] 
            for _ in range(num_pins):
                pin_x_rel = random.uniform(-r.w / 2, r.w / 2)
                pin_y_rel = random.uniform(-r.h / 2, r.h / 2)
                r.pins.append(Pin(pin_global_id, r, (pin_x_rel, pin_y_rel)))
                pin_global_id += 1
                new_pins_count += 1
        print(f"引腳生成完畢，總共生成了 {new_pins_count} 個新引腳。")
    
    def generate_edges(self, p_max, decay_rate, max_length_limit):
        """生成引腳之間的連線 (Netlist)"""
        print("\n開始生成 Netlist 連線...")
        # 論文中提到 netlist 是 hypergraph，這裡簡化為 pin-to-pin 的邊
        all_pins = [pin for r in self.rectangles for pin in r.pins]
        self.edges = []
        
        # 為了效率，可以先將 pins 按 x 座標排序或使用空間資料結構
        # 此處為簡化，仍使用 O(n^2) 的方法
        for i in range(len(all_pins)):
            for j in range(i + 1, len(all_pins)):
                pin1 = all_pins[i]; pin2 = all_pins[j]
                if pin1.parent_rect.id == pin2.parent_rect.id: continue

                pos1 = pin1.get_absolute_pos(); pos2 = pin2.get_absolute_pos()
                # 論文中使用 L1 距離 (Manhattan distance)
                distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

                if distance > max_length_limit: continue
                # 根據距離指數衰減的連接機率
                prob = p_max * math.exp(-decay_rate * distance)
                if random.random() < prob:
                    # 儲存 pin ID 對
                    self.edges.append((pin1.id, pin2.id))
        
        print(f"Netlist 生成完畢，總共生成了 {len(self.edges)} 條連線。")