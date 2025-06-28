import os
import json
import glob
import torch
from torch_geometric.data import Dataset, Data
from tqdm import tqdm

class FormattedLayoutDataset(Dataset):
    """
    用於載入您 `format_for_ml.py` 產出的 'formatted_*.json' 檔案的自訂 Dataset。
    它會即時地將 p, q, target 等鍵值對，轉換為 PyTorch Geometric 的 Data 物件。
    """
    def __init__(self, root, transform=None, pre_transform=None):
        """
        初始化 Dataset。
        Args:
            root (str): 存放 formatted_*.json 檔案的資料夾 (例如 'formatted_dataset')。
        """
        super().__init__(root, transform, pre_transform)

    @property
    def raw_file_names(self):
        # 我們直接處理根目錄下的檔案，所以這裡返回空列表。
        return []

    @property
    def processed_file_names(self):
        # 返回所有需要處理的 JSON 檔案的完整路徑列表。
        return sorted(glob.glob(os.path.join(self.root, 'formatted_*.json')))

    def download(self):
        pass # 我們假設資料已經存在。

    def process(self):
        # 因為我們是即時處理，所以這個函數什麼都不做。
        pass

    def len(self):
        return len(self.processed_file_names)

    def get(self, idx):
        """
        根據索引載入並處理單一的 JSON 檔案。
        這是這個類別的核心。
        """
        filepath = self.processed_file_names[idx]
        with open(filepath, 'r') as f:
            formatted_data = json.load(f)

        # --- 關鍵轉換：將您的格式映射到 PyG 的標準格式 ---

        # 節點特徵: p -> x
        node_features = torch.tensor(formatted_data['p'], dtype=torch.float)

        # 節點位置 (目標): target -> pos
        node_positions = torch.tensor(formatted_data['target'], dtype=torch.float)

        # 邊索引: edge_index -> edge_index (需要轉置)
        edge_index_list = formatted_data.get('edge_index', [])
        if edge_index_list:
            # 將 [[src, dst], ...] 的列表轉置為 [2, num_edges] 的張量
            edge_index = torch.tensor(edge_index_list, dtype=torch.long).t().contiguous()
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)

        # 邊屬性: q -> edge_attr
        edge_attr = torch.tensor(formatted_data.get('q', []), dtype=torch.float)

        # --- 創建並返回 Data 物件 ---
        data = Data(
            x=node_features,
            pos=node_positions,
            edge_index=edge_index,
            edge_attr=edge_attr
        )
        return data

# --- 使用範例 ---
if __name__ == '__main__':
    # 假設您格式化後的資料集儲存在名為 'formatted_dataset' 的資料夾中
    DATASET_ROOT_PATH = 'formatted_dataset'

    print(f"正在從 '{DATASET_ROOT_PATH}' 載入資料...")
    
    if not os.path.exists(DATASET_ROOT_PATH) or not glob.glob(os.path.join(DATASET_ROOT_PATH, 'formatted_*.json')):
        print(f"錯誤: 在 '{DATASET_ROOT_PATH}' 中找不到任何 'formatted_*.json' 檔案。")
        print("請先執行您提供的 format_for_ml.py 腳本。")
    else:
        try:
            # 建立 Dataset 物件
            dataset = FormattedLayoutDataset(root=DATASET_ROOT_PATH)
            
            print("-" * 50)
            print(f"資料集成功載入！")
            print(f"資料集中的圖數量: {len(dataset)}")
            print("-" * 50)

            # 檢查第一個資料點，以驗證格式轉換是否正確
            if len(dataset) > 0:
                first_data_point = dataset[0]
                print("驗證第一個資料點:")
                print(first_data_point)
                
                print("\n詳細資訊:")
                print(f"  節點數量: {first_data_point.num_nodes}")
                print(f"  邊數量: {first_data_point.num_edges}")
                print(f"  節點特徵維度 (x): {first_data_point.x.shape}")
                print(f"  節點位置維度 (pos): {first_data_point.pos.shape}")
                print(f"  邊索引維度 (edge_index): {first_data_point.edge_index.shape}")
                print(f"  邊屬性維度 (edge_attr): {first_data_point.edge_attr.shape}")

        except Exception as e:
            import traceback
            print(f"載入或處理資料時發生錯誤: {e}")
            traceback.print_exc()

