# 圖片等比例縮放工具

將目前目錄頂層的 JPEG、PNG 與 WebP 圖片完整縮入指定尺寸，維持原始比例、不裁切，也不放大小圖。成功處理後，原圖會移至 `originals/`，縮放後圖片則保留在目前目錄。

## 建立虛擬環境

需要 Python 3.10 以上版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell 啟用方式：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 使用方式

先切換至圖片所在目錄，再執行工具。

指定尺寸上限：

```bash
python /path/to/ResizeImg/resize_tool.py --size 1024x768
```

未指定尺寸時會顯示互動選單：

```bash
python /path/to/ResizeImg/resize_tool.py
```

選單包含：

- `1920x1080`
- `1600x1200`
- `1280x720`
- `1024x768`
- `800x600`

顯示範例如下：

```text
1. 1920x1080 / ≈ 350 KB / ≈ -42%
```

預估值以「所有來源檔案的平均大小 × 平均縮放後像素比例」計算。這是快速粗估；實際檔案大小仍會受圖片內容、格式及壓縮方式影響。

## 輸出規則

例如 `photo.jpg` 的原始尺寸為 `2000x1000`，指定 `1024x768` 後：

```text
目前目錄/
├── photo_1024x512.jpg
└── originals/
    └── photo.jpg
```

- 尺寸字尾使用實際輸出尺寸，而非尺寸框上限。
- EXIF 方向會先校正；可沿用時會保留 EXIF 與 ICC 色彩描述。
- PNG 與 WebP 的透明度會保留。
- 已帶 `_寬x高` 字尾的圖片不會再次處理。
- 若輸出檔或同名備份已存在，來源圖片會保持原位並被跳過，不會覆寫既有檔案。
- 個別圖片失敗不會中止其他圖片；結束時會顯示成功、跳過與失敗數量。

## 執行測試

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```
