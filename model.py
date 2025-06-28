# model.py

import torch
import torch.nn as nn
import math
from torch_geometric.nn import GATv2Conv
from torch_geometric.data import Data

class SinusoidalEmbedding(nn.Module):
    """
    正弦/餘弦位置或時間嵌入。
    """
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        """
        Args:
            x (torch.Tensor): 輸入張量，形狀為 (batch_size, 1) 或 (num_nodes, 2)
        
        Returns:
            torch.Tensor: 嵌入後的張量，形狀為 (batch_size, dim) 或 (num_nodes, dim)
        """
        device = x.device
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)
        
        # 處理一維時間戳或二維座標
        if len(x.shape) == 2 and x.shape[1] == 1: # Timestep (1D)
            emb = x * emb.unsqueeze(0)
            emb = torch.cat([emb.sin(), emb.cos()], dim=-1)
            # 如果 dim 是奇數，補零
            if self.dim % 2 == 1:
                emb = nn.functional.pad(emb, (0, 1))

        elif len(x.shape) == 2 and x.shape[1] == 2: # Position (2D)
            # 將 pos (N, 2) -> (N, 2, 1) * emb (1, half_dim) -> (N, 2, half_dim)
            emb = x.unsqueeze(-1) * emb.unsqueeze(0)
            # 分別計算 sin 和 cos，然後交錯合併
            sin_emb = emb.sin().view(x.shape[0], -1)
            cos_emb = emb.cos().view(x.shape[0], -1)
            # 將 sin_emb 和 cos_emb 合併成最終的 emb
            # 這裡我們只取一半的 sin 和一半的 cos，以確保總維度正確
            emb = torch.cat([sin_emb[:, :half_dim], cos_emb[:, :half_dim]], dim=1)
            # 如果維度不匹配，進行調整
            if emb.shape[1] != self.dim:
                emb = nn.functional.pad(emb, (0, self.dim - emb.shape[1]))
        else:
            raise ValueError("Input to SinusoidalEmbedding must have shape (N, 1) for time or (N, 2) for position.")

        return emb


class ResGNNBlock(nn.Module):
    """
    論文圖 2 中的 ResGNN block。
    包含兩個 GNN 層和一個殘差連接。
    """
    def __init__(self, model_dim, num_heads, edge_dim):
        super().__init__()
        # 根據論文附錄，GNN 層使用 GATv2
        self.gnn1 = GATv2Conv(model_dim, model_dim, heads=num_heads, edge_dim=edge_dim, concat=False)
        self.norm1 = nn.LayerNorm(model_dim)
        self.gnn2 = GATv2Conv(model_dim, model_dim, heads=num_heads, edge_dim=edge_dim, concat=False)
        self.norm2 = nn.LayerNorm(model_dim)
        self.activation = nn.GELU()

    def forward(self, h, edge_index, edge_attr):
        identity = h
        
        h = self.gnn1(h, edge_index, edge_attr)
        h = self.norm1(h)
        h = self.activation(h)
        
        h = self.gnn2(h, edge_index, edge_attr)
        h = self.norm2(h)
        
        # 殘差連接
        return self.activation(h + identity)

class DenoisingModel(nn.Module):
    """
    根據論文 "Chip Placement with Diffusion" 實現的去噪模型。
    此版本實現了 Encoder 和 ResGNN block 部分。
    """
    def __init__(self, node_feature_dim, edge_feature_dim, model_dim=128, num_heads=4):
        """
        Args:
            node_feature_dim (int): 節點特徵的維度 (p)，通常是 2 (正規化寬高)。
            edge_feature_dim (int): 邊特徵的維度 (q)，通常是 4 (源/目標引腳相對位置)。
            model_dim (int): 模型內部的主要隱藏層維度。
            num_heads (int): GATv2 注意力頭的數量。
        """
        super().__init__()

        # --- 1. Encoder 部分 ---
        # 論文中提到，模型接收 2D 正弦位置編碼以及原始 (x,y) 座標 。
        # 同時也需要對時間步 t 和節點自身特徵 p 進行編碼。
        
        # 時間嵌入
        self.time_embedding = SinusoidalEmbedding(model_dim)
        self.time_proj = nn.Sequential(
            nn.Linear(model_dim, model_dim),
            nn.GELU(),
            nn.Linear(model_dim, model_dim)
        )

        # 位置 (pos, 即 x_t) 嵌入
        self.pos_embedding = SinusoidalEmbedding(model_dim)
        self.pos_proj = nn.Sequential(
            nn.Linear(model_dim, model_dim),
            nn.GELU(),
            nn.Linear(model_dim, model_dim)
        )

        # 節點特徵 (p) 嵌入
        self.node_feature_proj = nn.Linear(node_feature_dim, model_dim)

        # 原始 (x,y) 座標的線性投影 
        self.raw_pos_proj = nn.Linear(2, model_dim)

        # --- 2. ResGNN Block 部分 ---
        # 根據論文，GNN 層和 Attention 層交錯使用以獲得更好的表達能力 [cite: 64]。
        # 此處我們實現 ResGNN Block。
        self.res_gnn_block = ResGNNBlock(model_dim, num_heads, edge_feature_dim)
        
        # --- 3. 輸出層 ---
        # 模型的最終目標是預測加到 pos 上的噪聲，其維度為 2 (dx, dy)。
        self.output_proj = nn.Sequential(
            nn.Linear(model_dim, model_dim // 2),
            nn.GELU(),
            nn.Linear(model_dim // 2, 2)
        )

    # model.py -> DenoisingModel -> forward (替換整個函數)

    def forward(self, data, t):
        """
        模型的前向傳播。

        Args:
            data (torch_geometric.data.Data): 包含圖結構的資料物件。
                - data.x: 節點特徵 (p), shape: [num_nodes, node_feature_dim]
                - data.pos: 帶噪聲的節點位置 (x_t), shape: [num_nodes, 2]
                - data.edge_index: 邊索引, shape: [2, num_edges]
                - data.edge_attr: 邊特徵 (q), shape: [num_edges, edge_feature_dim]
                - data.batch: 節點到其所屬圖的映射, shape: [num_nodes]
            t (torch.Tensor): 當前的時間步，shape: [batch_size]

        Returns:
            torch.Tensor: 預測的噪聲，shape: [num_nodes, 2]
        """
        # 1. 進行編碼 (Encoder)
        # t 形狀為 [batch_size], 嵌入後 time_emb 形狀為 [batch_size, model_dim]
        time_emb = self.time_embedding(t.unsqueeze(-1).float())
        time_emb = self.time_proj(time_emb)

        pos_emb = self.pos_embedding(data.pos)
        pos_emb = self.pos_proj(pos_emb)

        node_feat_emb = self.node_feature_proj(data.x)
        raw_pos_emb = self.raw_pos_proj(data.pos)
        
        # 將所有嵌入相加以組合資訊
        # 使用 data.batch 進行索引，為每個節點分配其對應圖的時間嵌入
        time_emb_expanded = time_emb[data.batch] 
        h = node_feat_emb + pos_emb + raw_pos_emb + time_emb_expanded

        # 2. 通過 ResGNN Block
        h = self.res_gnn_block(h, data.edge_index, data.edge_attr)
        
        # 3. 預測輸出
        predicted_noise = self.output_proj(h)

        return predicted_noise

# --- 使用範例 ---
if __name__ == '__main__':
    # 假設參數
    NUM_NODES = 230
    NUM_EDGES = 1400
    NODE_DIM = 2 # width, height
    EDGE_DIM = 4 # pin rel_pos x,y for src and dst
    MODEL_DIM = 128
    
    # 建立模型
    model = DenoisingModel(
        node_feature_dim=NODE_DIM, 
        edge_feature_dim=EDGE_DIM, 
        model_dim=MODEL_DIM
    )
    
    print("模型架構:")
    print(model)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n模型總參數數量: {total_params:,}")

    # 建立一個假的資料點來測試前向傳播
    dummy_x = torch.randn(NUM_NODES, NODE_DIM)
    dummy_pos = torch.randn(NUM_NODES, 2) # 模擬帶噪聲的座標
    dummy_edge_index = torch.randint(0, NUM_NODES, (2, NUM_EDGES), dtype=torch.long)
    dummy_edge_attr = torch.randn(NUM_EDGES, EDGE_DIM)
    dummy_t = torch.tensor([500]) # 假的時間步 (0-1000)

    dummy_data = Data(x=dummy_x, pos=dummy_pos, edge_index=dummy_edge_index, edge_attr=dummy_edge_attr)

    print(f"\n輸入資料點 (data): {dummy_data}")
    print(f"輸入時間步 (t): {dummy_t}")
    
    # 執行前向傳播
    try:
        predicted_noise = model(dummy_data, dummy_t)
        print(f"\n成功執行前向傳播！")
        print(f"輸出 (預測的噪聲) shape: {predicted_noise.shape}")
        assert predicted_noise.shape == (NUM_NODES, 2)
        print("輸出 Shape 正確！")
    except Exception as e:
        import traceback
        print(f"\n前向傳播時發生錯誤: {e}")
        traceback.print_exc()