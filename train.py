# train.py

import torch
import torch.nn as nn
import yaml
import os
import argparse
from tqdm import tqdm

from torch_geometric.loader import DataLoader
from prepare_input import FormattedLayoutDataset
from model import DenoisingModel

# --- Diffusion Helpers ---

def linear_beta_schedule(timesteps, beta_start, beta_end):
    """
    產生線性的噪聲調度表 (beta schedule)。
    """
    return torch.linspace(beta_start, beta_end, timesteps)

def gather(consts, t):
    """
    根據時間步 t 收集對應的常數。
    """
    c = consts.gather(-1, t)
    return c.reshape(-1, 1, 1)

# --- Main Training Function ---

def train(config_path):
    """
    主訓練函數。
    """
    # 1. 載入設定
    with open(config_path, 'r', encoding='utf-8') as f: # <--- 在這裡加上 encoding='utf-8'
        config = yaml.safe_load(f)

    m_params = config['model_params']
    t_params = config['training_params']
    d_params = config['diffusion_params']
    io_params = config['io_params']

    # 2. 設定環境
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    os.makedirs(io_params['output_dir'], exist_ok=True)

    # 3. 準備 Diffusion 相關常數
    T = d_params['timesteps']
    betas = linear_beta_schedule(T, d_params['beta_start'], d_params['beta_end']).to(device)
    alphas = 1. - betas
    alphas_cumprod = torch.cumprod(alphas, axis=0)
    
    sqrt_alphas_cumprod = torch.sqrt(alphas_cumprod)
    sqrt_one_minus_alphas_cumprod = torch.sqrt(1. - alphas_cumprod)

    # 4. 準備資料集
    # 假設節點和邊的特徵維度是固定的，我們可以從第一個樣本中推斷
    # 更好的做法是在 format_for_ml.py 中將維度資訊存儲下來
    # 為了簡化，我們先手動設定
    node_feature_dim = 2 # p: [width, height]
    edge_feature_dim = 4 # q: [src_pin_rel_x, src_pin_rel_y, dst_pin_rel_x, dst_pin_rel_y]
    
    dataset = FormattedLayoutDataset(root=io_params['dataset_dir'])
    dataloader = DataLoader(dataset, batch_size=t_params['batch_size'], shuffle=True)
    print(f"Dataset loaded with {len(dataset)} samples.")

    # 5. 建立模型、優化器和損失函數
    model = DenoisingModel(
        node_feature_dim=node_feature_dim,
        edge_feature_dim=edge_feature_dim,
        model_dim=m_params['model_dim'],
        num_heads=m_params['num_heads']
    ).to(device)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=t_params['learning_rate'])
    loss_fn = nn.MSELoss() # 論文通常使用 L1 或 L2 Loss 來比較預測噪聲和真實噪聲
    
    print(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters.")
    
    # 6. 訓練迴圈
    for epoch in range(t_params['epochs']):
        model.train()
        total_loss = 0.0
        
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{t_params['epochs']}")
        for batch in progress_bar:
            batch = batch.to(device)
            optimizer.zero_grad()

            # --- Diffusion Forward Process ---
            # (1) 取得乾淨的資料 (x_0)，這裡指的是元件的真實位置
            clean_pos = batch.pos

            # (2) 為批次中的每個圖隨機採樣一個時間步 t
            # batch.batch 是一個張量，標示每個節點屬於哪個圖
            num_graphs_in_batch = batch.num_graphs
            t = torch.randint(0, T, (num_graphs_in_batch,), device=device).long()

            # (3) 採樣高斯噪聲
            noise = torch.randn_like(clean_pos)
            
            # (4) 計算加噪後的位置 (x_t)
            # gather 函數會根據每個圖的時間步 t，選取對應的常數
            # [t[batch.batch]] 會將每個節點映射到其所屬圖的時間步 t
            sqrt_alpha_t = sqrt_alphas_cumprod[t[batch.batch]].unsqueeze(-1)
            sqrt_one_minus_alpha_t = sqrt_one_minus_alphas_cumprod[t[batch.batch]].unsqueeze(-1)
            noisy_pos = sqrt_alpha_t * clean_pos + sqrt_one_minus_alpha_t * noise
            
            # (5) 使用加噪後的位置來預測噪聲
            batch.pos = noisy_pos # 更新 batch 中的 pos 以便傳入模型
            predicted_noise = model(batch, t)
            
            # (6) 計算損失
            loss = loss_fn(predicted_noise, noise)
            
            # (7) 反向傳播與優化
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            progress_bar.set_postfix(loss=loss.item())

        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1} | Average Loss: {avg_loss:.6f}")

        # 7. 儲存模型權重
        if (epoch + 1) % io_params['save_checkpoint_every'] == 0 or (epoch + 1) == t_params['epochs']:
            checkpoint_path = os.path.join(io_params['output_dir'], f"model_epoch_{epoch+1}.pth")
            torch.save(model.state_dict(), checkpoint_path)
            print(f"Saved checkpoint to {checkpoint_path}")

    print("\nTraining complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a Denoising Diffusion Model for Chip Placement.")
    parser.add_argument(
        "--config", 
        type=str, 
        default="train_config.yaml",
        help="Path to the training configuration YAML file."
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}")
    else:
        train(args.config)