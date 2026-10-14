# PersonalCDN

### CDN URL

這個倉庫推上 GitHub 之後，裡面的檔案可以透過 jsDelivr 直接取用。把檔案在倉庫裡的路徑接在網址後面即可，路徑從倉庫根目錄算起，開頭不要加 `/`。

```
https://cdn.jsdelivr.net/gh/keoinn/personalcdn/[檔案路徑]
```

例如倉庫裡的 `images/assets/avatars/coding-cat.png`，對應網址是：

```
https://cdn.jsdelivr.net/gh/keoinn/personalcdn/images/assets/avatars/coding-cat.png
```

在文章裡可以這樣引用：

```markdown
![coding cat](https://cdn.jsdelivr.net/gh/keoinn/personalcdn/images/assets/avatars/coding-cat.png)
```

檔案要先 commit 並 push 到 `main`，網址才會生效。更新後若短時間內仍看到舊檔，是 jsDelivr 的快取還沒更新。

## ResizeImg

等比例縮放目前目錄頂層的 JPEG、PNG 與 WebP。圖片會完整縮入指定尺寸，維持原始比例、不裁切，也不放大小圖。成功後原圖移到 `originals/`，縮放後的圖片留在目前目錄。

需要 Python 3.10 以上。在工具目錄建立虛擬環境：

```bash
cd tools/ResizeImg
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

切換到圖片所在目錄後執行。指定尺寸上限：

```bash
python /path/to/HexoBlog-CDN/tools/ResizeImg/resize_tool.py --size 1024x768
```

未指定尺寸時會顯示互動選單，預設選項為 `1920x1080`、`1600x1200`、`1280x720`、`1024x768`、`800x600`。每一項會附上粗估的輸出大小與變化百分比。

例如 `photo.jpg` 原始尺寸為 `2000x1000`，指定 `1024x768` 後：

```text
目前目錄/
├── photo_1024x512.jpg
└── originals/
    └── photo.jpg
```

- 檔名字尾是實際輸出尺寸，不是尺寸框上限。
- EXIF 方向會先校正；可沿用時會保留 EXIF 與 ICC 色彩描述。
- PNG 與 WebP 的透明度會保留。
- 已帶 `_寬x高` 字尾的圖片不會再次處理。
- 輸出檔或同名備份已存在時，來源圖片保持原位並跳過，不會覆寫。
- 單張失敗不會中止其他圖片；結束時會顯示成功、跳過與失敗數量。

## RenameImg

把程式所在資料夾裡的圖片依修改時間由舊到新重新命名。只使用 Python 標準函式庫。

支援的副檔名：`.jpg`、`.jpeg`、`.png`、`.gif`、`.bmp`、`.webp`、`.tif`、`.tiff`。

先把要處理的圖片放到 `tools/RenameImg/`，再執行：

```bash
python tools/RenameImg/rename_images.py
```

程式會詢問檔名前綴，掃描同資料夾裡已使用的編號，列出預覽後再確認。輸入 `y` 或 `yes` 才會改名。

編號固定 3 位數，並接在目前最大編號之後。例如資料夾裡已有 `openrouter-applies-005.jpg`，下一個會是 `openrouter-applies-006`：

```text
photo.jpg -> openrouter-applies-006.jpg
shot.png  -> openrouter-applies-007.png
```

- 已符合 `前綴-數字` 的圖片會跳過。
- 改名分兩階段，先換成臨時檔名再換成正式名稱，避免檔名互相衝突。
