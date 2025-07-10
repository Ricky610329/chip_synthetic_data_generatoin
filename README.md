# Chip Synthetic Data Generation

## 專案總覽

本專案是一個用於**生成複雜二維積體電路佈局樣本**的工具鏈。其核心目標是透過一個受物理特性約束的、具備隨機性的演算法，自動產生大量多樣化的佈局資料集。**此版本新增了生成預定義類比對稱結構的功能，並能將這些結構在機器學習格式化階段抽象化為單一節點，讓模型能以更宏觀的視角學習佈局**。

整個流程包含四個主要階段：
1.  **參數化組態**：透過 `config.yaml` 靈活定義生成規則，**包含對稱結構的生成規則**。
2.  **佈局生成**：執行 `main.py`，根據組態產生包含**固定對稱群組**、元件、引腳和連線的原始佈局資料。
3.  **分析與視覺化**：使用 `analyze_layout.py` 對單一樣本進行視覺化繪圖與數據統計分析。
4.  **機器學習格式化**：執行 `format_for_ml.py` 將整批原始資料轉換為模型訓練所需的圖結構資料，**此步驟會進行對稱群組的抽象化**。
---

## 檔案結構與功能說明

### 1. `config.yaml` - 參數設定檔

這是整個生成流程的控制中心，定義了所有固定與隨機參數。

-   **`run_settings`**: 設定執行參數，例如要產生的樣本總數 (`num_samples_to_generate`) 和輸出的資料夾名稱 (`output_directory`)。
-   **`analog_symmetry_settings`**: ***(新功能)*** 用於定義對稱類比電路群組的生成規則。
    -   `enable`: 是否啟用此功能。
    -   `num_groups`: 在每個樣本中生成多少個對稱群組。
    -   `group_configs`: 定義不同類型對稱群組的生成規則與權重，例如 `quad` (四方佈局)、`vertical` (垂直對稱)、`horizontal` (水平對稱)。
    -   `component_width_range`, `component_height_range`: 對稱元件的尺寸範圍。
    -   `group_gap_range`: 對稱元件之間的間隙範圍。
    -   `pins_per_component`: 為每個對稱元件生成的引腳數量。
-   **`base_params`**: 定義固定不變的基礎參數。這些是演算法的核心常數，例如畫布尺寸、最大迭代次數、生長步長、停滯與抖動的觸發條件等。
-   **`randomize_params`**: **此專案的關鍵特色**。定義了在每一輪樣本生成時需要隨機化的參數。可以指定參數的隨機類型（如整數 `randint`、浮點數 `uniform`、或一對浮點數 `uniform_pair`）及其上下限範圍。這確保了生成的每個樣本都具有獨特的特性（如不同的元件數量、密度、長寬比限制等）。**注意：當啟用對稱生成時，`NUM_RECTANGLES` 代表「非對稱」元件的數量**。

### 2. `main.py` - 主執行腳本

這是啟動資料集生成的進入點。

-   **讀取設定**: 首先會載入 `config.yaml` 的設定。
-   **生成迴圈**: 根據 `num_samples_to_generate` 的值，多次執行生成流程。
-   **參數隨機化**: 在每次迴圈中，呼叫 `get_randomized_params` 函數，根據 `randomize_params` 中的規則產生一組本次專用的參數。
-   **設定種子**: 為 `random` 和 `numpy` 設定隨機種子，確保每次執行的結果可以被重現（種子本身會被儲存）。
-   **執行生成**:
    -   **階段一：對稱群組生成**：如果啟用，首先呼叫 `SymmetricGenerator` 放置固定的、帶有引腳的對稱元件群組，並記錄下最後使用的 ID。
    -   **階段二：隨機元件填充**：在剩餘空間中放置指定數量的基礎元件。
    -   **階段三：優化與完成**：實例化 `LayoutGenerator` 進行迭代生長，接著呼叫 `generate_pins()` (為非對稱元件) 和 `generate_edges()` 來完成引腳和連線的生成。
-   **儲存結果**: 將生成的 `Layout` 物件（**包含 `group_id` 等新屬性**）及該次使用的參數序列化為 JSON 格式，並儲存到指定的輸出資料夾中。

### 3. `symmetry.py` - 對稱群組生成器

一個專門用來生成具有嚴格對稱性的類比電路群組的模組。

-   **`SymmetricGenerator` 類**:
    -   `generate_analog_groups()`: 根據 `config.yaml` 的設定，生成多個對稱群組。
    -   **群組標記**: 為屬於同一個對稱結構的所有元件分配一個**共同的 `group_id`** (例如 `"sym_group_0"`) 和 `group_type`。這個 ID 是後續 ML 格式化進行節點抽象化的關鍵。
    -   **引腳對稱**: 在生成對稱元件時，其引腳的位置也嚴格遵循對稱規則（例如，垂直對稱的元件，其引腳 x 座標相反，y 座標相同）。
    -   **放置策略**: 採用隨機嘗試的方式，在畫布上找到足夠的空白空間來放置整個群組，確保不與已放置的元件重疊。

### 4. `generator.py` - 核心佈局生成器

此檔案封裝了佈局生成的核心演算法，是整個專案技術含量最高的部分。

-   **`LayoutGenerator` 類**:
    -   `generate()`: 演算法主體。採用「智慧成長」策略，從一堆隨機分佈的 1x1 元件開始，根據其「成長機率」（區分為 Macro 元件和標準元件）進行迭代增長。
    -   **碰撞檢測**: 在每一步增長後，都會檢查是否與其他元件重疊，若重疊則復原該次增長。同時也會檢查是否超出畫布邊界或違反最大長寬比限制。
    -   **停滯處理機制**: 當佈局無法繼續自然增長時，會觸發一系列複雜的應對策略：
        -   `_rollback_growth`: 將所有元件的尺寸縮小幾步，以創造新的生長空間。
        -   `_shake_components`: 對元件進行「抖動」，透過模擬物理排斥力將重疊的元件推開，或為卡住的元件創造空隙。此方法分為輕量抖動和最終強制合法化兩種模式。
        -   `_infill_empty_spaces`: 當抖動多次後仍無法有效增長時，此機制會掃描畫布上的空白區域，並在其中隨機投放新的小元件，以提高整體密度。
    -   **適應固定元件**: 其核心演算法現在會識別並**跳過** `rect.fixed == True` 的元件（即來自 `SymmetricGenerator` 的元件），確保這些預先佈局好的對稱結構在後續優化過程中保持其完整性和位置。
-   **`QuadTree` 類**:
    -   一個四分樹資料結構，作為演算法的加速工具。在 `_shake_components` 階段，它被用來快速查詢一個元件附近的鄰居，避免了 O(N²) 的全域遍歷，大幅提升了碰撞檢測的效率。

### 5. `layout.py` - 核心資料結構

此檔案定義了構成一個「佈局」的基礎物件。

-   **`Rectangle` 類**: 代表一個元件。儲存其 ID、中心座標 (x, y)、寬高 (w, h) 以及其自身的成長機率。***(新特性)*** **新增了 `group_id` 和 `group_type` 屬性**，用於標識其所屬的對稱群組，以及 `fixed` 屬性來標記其是否為固定元件。
-   **`Pin` 類**: 代表一個引腳。儲存其全域 ID、所屬的父元件 (`parent_rect`)，以及相對於父元件中心的座標 (`rel_pos`)。
-   **`Layout` 類**: 代表一個完整的佈局。它包含畫布尺寸、所有 `Rectangle` 物件的列表，以及所有 `Edge`（連線）的列表。
    -   `generate_pins()`: 根據**Rent's Rule** (`k * area^p`) 為每個元件計算並生成其應有的引腳數量和隨機位置。***(新特性)*** **此函式現在只為非固定的元件生成引腳**，並能接收一個 `start_pin_id` 參數，以確保 ID 不會與對稱元件已有的引腳 ID 衝突。
    -   `generate_edges()`: 在不同元件的引腳之間建立連線。兩點間的連線機率與其**曼哈頓距離**成反比，遵循**指數衰減**模型 (`p_max * exp(-decay_rate * distance)`)。同時，超過 `max_length_limit` 的超長連線會被直接忽略。

### 6. `analyze_layout.py` - 視覺化與分析工具

一個後處理腳本，用於深入理解單個生成的樣本。

-   **視覺化**: 使用 `matplotlib` 將 JSON 檔案中的佈局繪製出來。
    -   不同類型的元件（Macro vs. Standard）會以不同顏色顯示。
    -   元件的 ID 會標註在中心。
    -   所有的引腳間連線（紅色線段）也會被繪製出來。
-   **統計分析**: 計算並印出一份分析報告，包含：
    -   元件、引腳、連線的總數。
    -   連線線長（Wirelength）的統計數據，如總線長、平均值、中位數、最大/最小值等。

### 7. `visualize_abstraction.py` - 抽象化視覺化工具

一個用於清晰地展示 `format_for_ml.py` 的抽象化過程的後處理腳本。

-   **功能**: 該工具會生成一張對比圖，包含兩個子圖：
    1.  **左圖 (Original Detailed Layout)**: 顯示真實的物理佈局，對稱元件會以不同顏色標示。
    2.  **右圖 (Abstracted View)**: 顯示 GNN 模型「眼中」的佈局。對稱元件群組被一個**虛線邊界框**取代，代表一個抽象節點，而獨立元件則保持原樣。
-   **用途**: 幫助使用者理解模型學習的目標是放置這些抽象節點，而非單一的微小元件。

### 8. `format_for_ml.py` - 機器學習格式化與群組抽象化工具

將原始 JSON 資料集轉換為適用於圖機器學習模型的格式。

-   **平行處理**: 使用 `multiprocessing` 模組，能夠利用多核心 CPU 並行處理大量檔案，效率極高。
-   **群組抽象化**:
    -   此腳本不再將每個元件視為一個獨立節點。它會遍歷所有元件，將擁有相同 `group_id` 的元件**合併**成一個**單一的抽象節點**。
    -   對於獨立的元件，則依然視為一個節點。
-   **格式轉換**: 將每個 layout JSON 轉換為包含以下鍵的字典：
    -   `p`: **節點特徵 (Node Features)**。每個節點（對於群組，是其**邊界框**）的正規化寬和高。
    -   `target`: **目標輸出 (Target Placements)**。每個節點最終的正規化中心位置 (x, y)。
    -   `edge_index`: **邊索引 (Edge Index)**。以 COO 格式儲存的圖連接性，即哪些抽象化後的節點之間有連線。
    -   `q`: **邊特徵 (Edge Attributes)**。每條邊對應的源和目標引腳的正規化相對位置（相對於節點中心）。
    -   `sub_components`: ***(新欄位)*** 儲存每個節點內部元件的資訊（相對於節點中心的偏移量和實際尺寸），用於在模型預測完成後**還原**詳細的佈局。
-   **錯誤處理**: 能捕捉並報告在處理單一檔案時發生的錯誤，確保整個轉換過程不會因少數問題檔案而中斷。

### 9. `merge_datasets.py` - 合併不同的資料集

一個簡單的命令列工具，可將兩個獨立生成的資料夾合併成一個，並自動重新編號檔案，方便擴充資料集。
-   **使用**
    ```bash
    python merge_datasets.py dataset_A dataset_B merged_dataset
    ```
### 10. `demo_generator.py` - 動態生成過程展示工具

一個用於生成 `layout_generation_demo.gif` 的腳本。它繼承自 `LayoutGenerator` 並在關鍵步驟中插入儲存影格的邏輯，以動態展示新的、分階段的生成流程：
1.  首先在畫布上放置固定的對稱群組（帶有引腳）。
2.  接著放置隨機的初始元件。
3.  最後執行生長、抖動、填充等一系列優化演算法。

---

## 如何使用

1.  **組態參數**:
    -   打開 `config.yaml` 檔案。
    -   在 `analog_symmetry_settings` 中組態您想要的對稱群組生成規則，或將 `enable` 設為 `false` 來停用此功能。
    -   在 `run_settings` 中設定您想生成的樣本數量。
    -   根據需求調整 `base_params` 和 `randomize_params` 中的規則。

2.  **生成原始資料集**:
    -   在終端機中執行 `python main.py`。
    -   程式會開始生成樣本，並將結果（`layout_xxx.json`）儲存在 `config.yaml` 中指定的 `output_directory` 資料夾內。

3.  **分析單一樣本 (可選)**:
    -   執行 `python analyze_layout.py <path_to_your_json_file>`，例如：
        ```bash
        python analyze_layout.py dataset/layout_1.json
        ```
    -   程式會顯示該佈局的視覺化圖表和統計報告。

4.  **格式化整個資料集以供模型訓練**:
    -   執行 `python format_for_ml.py <input_directory> <output_directory>`，例如：
        ```bash
        python format_for_ml.py dataset/ formatted_dataset/
        ```
    -   程式會讀取 `dataset/` 中的所有 JSON 檔案，將它們轉換為 ML-ready 格式（**包含群組抽象化**），並將新檔案儲存到 `formatted_dataset/` 中。

5.  **(推薦) 視覺化檢查抽象結果**:
    -   執行 `python visualize_abstraction.py <path_to_original_json> <output_image_name.png>`，例如：
        ```bash
        visualize_abstraction.py dataset_symmetry/layout_1.json abstraction_view_1.png
        ```
    -   打開生成的圖片，確認左邊的詳細佈局與右邊的抽象化視圖符合預期。

## Demo

![image](layout_generation_demo.gif)

## Reference

Lee, V., Deng, C., Elzeiny, L., Abbeel, P., & Wawrzynek, J. (2024).
[Chip Placement with Diffusion](https://arxiv.org/abs/2407.12282v1). *arXiv:2407.12282v1 [cs.LG]*.