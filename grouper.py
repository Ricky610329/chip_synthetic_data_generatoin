# grouper.py (Corrected)

import random
import math
from collections import defaultdict

class LayoutGrouper:
    """
    負責在一個已生成的佈局基礎上，建立階層式的、非對稱的群組。
    """
    def __init__(self, layout, params):
        self.layout = layout
        self.params = params
        self.config = params['grouping_settings']

    def _get_placeable_items(self):
        """
        將佈局中的元件和現有群組抽象化為可放置的「項目」。
        每個項目包含其中心點、所含元件的ID列表，以及它自身的ID。
        """
        items = []
        
        # 1. 處理已有的對稱群組或其它群組
        existing_groups = defaultdict(list)
        single_rects = []
        for r in self.layout.rectangles:
            if r.group_id:
                existing_groups[r.group_id].append(r)
            else:
                single_rects.append(r)
        
        for group_id, rects_in_group in existing_groups.items():
            min_x = min(r.x - r.w/2 for r in rects_in_group)
            max_x = max(r.x + r.w/2 for r in rects_in_group)
            min_y = min(r.y - r.h/2 for r in rects_in_group)
            max_y = max(r.y + r.h/2 for r in rects_in_group)
            
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            
            items.append({
                "id": group_id,
                "center": (center_x, center_y),
                "rect_ids": [r.id for r in rects_in_group],
                "is_group": True
            })
            
        # 2. 處理單一元件
        for r in single_rects:
            items.append({
                "id": r.id,
                "center": (r.x, r.y),
                "rect_ids": [r.id],
                "is_group": False
            })
            
        return items

    def create_hierarchical_groups(self):
        """
        執行分組主邏輯。
        """
        if self.config['method'] != 'proximity':
            print("Warning: Only 'proximity' grouping method is supported.")
            return self.layout

        items = self._get_placeable_items()
        
        # ✨ FIX: Correctly read 'low' and 'high' values from the config dictionary
        num_groups_config = self.config['num_groups_to_create']
        num_groups_to_create = random.randint(num_groups_config['low'], num_groups_config['high'])
        
        # 標記哪些項目已經被分到新的大群組中
        grouped_item_indices = set()
        
        print(f"\nAttempting to create {num_groups_to_create} hierarchical groups...")

        for i in range(num_groups_to_create):
            available_indices = [idx for idx in range(len(items)) if idx not in grouped_item_indices]
            if not available_indices:
                print("No more available items to form new groups.")
                break

            # 1. 隨機選擇一個「種子」項目
            seed_idx = random.choice(available_indices)
            seed_item = items[seed_idx]
            
            # ✨ FIX: Correctly read 'low' and 'high' values for items_per_group as well
            items_per_group_config = self.config['items_per_group']
            items_per_group = random.randint(items_per_group_config['low'], items_per_group_config['high'])
            num_neighbors_to_find = items_per_group - 1

            if num_neighbors_to_find <= 0:
                continue

            # 2. 尋找種子項目的 K 個最近鄰居
            distances = []
            for j in available_indices:
                if j == seed_idx:
                    continue
                other_item = items[j]
                dist = math.hypot(seed_item['center'][0] - other_item['center'][0], 
                                  seed_item['center'][1] - other_item['center'][1])
                distances.append((dist, j))
            
            distances.sort(key=lambda x: x[0])
            
            neighbors_indices = [idx for _, idx in distances[:num_neighbors_to_find]]
            
            # 3. 建立新群組並更新元件屬性
            new_group_members_indices = [seed_idx] + neighbors_indices
            if len(new_group_members_indices) < 2:
                continue

            # 為這個新群組產生一個唯一的ID
            new_group_id = f"h_group_{i}"
            
            member_ids_for_print = [items[idx]['id'] for idx in new_group_members_indices]
            print(f"  - Creating group '{new_group_id}' with items: {member_ids_for_print}")

            all_rect_ids_in_new_group = set()
            for member_idx in new_group_members_indices:
                all_rect_ids_in_new_group.update(items[member_idx]['rect_ids'])
            
            # 4. **關鍵步驟**：修改 layout 中實際 Rectangle 物件的 group_id
            for r in self.layout.rectangles:
                if r.id in all_rect_ids_in_new_group:
                    r.group_id = new_group_id
                    r.group_type = 'hierarchical' # 標記為新的群組類型
            
            # 標記這些項目已被使用
            grouped_item_indices.update(new_group_members_indices)

        print("--- Hierarchical grouping complete. ---")
        return self.layout