from pathlib import Path
from datetime import datetime
import uuid
import re


# ============================================================
# 設定
# ============================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


# ============================================================
# 找出目前已使用的編號
# ============================================================

def get_next_serial_number(folder: Path, prefix: str) -> int:
    """
    掃描資料夾內目前已存在的檔案。

    例如：

        openrouter-applies-001.jpg
        openrouter-applies-002.png
        openrouter-applies-005.jpg

    下一個編號會是：

        006
    """

    pattern = re.compile(
        rf"^{re.escape(prefix)}-(\d+)$"
    )

    max_number = 0

    for path in folder.iterdir():

        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        match = pattern.match(path.stem)

        if match:
            number = int(match.group(1))

            if number > max_number:
                max_number = number

    return max_number + 1


# ============================================================
# 取得尚未處理的圖片
# ============================================================

def get_images(folder: Path, prefix: str):
    """
    找出尚未重新命名的圖片。

    已經符合：

        prefix-數字

    格式的圖片會自動排除。
    """

    pattern = re.compile(
        rf"^{re.escape(prefix)}-(\d+)$"
    )

    images = []

    for path in folder.iterdir():

        # 必須是檔案
        if not path.is_file():
            continue

        # 必須是圖片
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        # 已經是輸出檔案，跳過
        if pattern.match(path.stem):
            continue

        images.append(path)

    # 按照檔案修改時間由舊到新排序
    images.sort(
        key=lambda path: path.stat().st_mtime
    )

    return images


# ============================================================
# 重新命名
# ============================================================

def rename_images(
    folder: Path,
    images,
    prefix: str,
    start_number: int
):
    """
    將圖片重新命名。

    例如：

        openrouter-applies-004.jpg
        openrouter-applies-005.jpg
        openrouter-applies-006.png
    """

    temporary_files = []

    # --------------------------------------------------------
    # 第一階段：
    # 先改成臨時名稱。
    #
    # 避免原始檔名與新檔名發生衝突。
    # --------------------------------------------------------

    for image in images:

        temp_name = (
            f".__rename_temp_"
            f"{uuid.uuid4().hex}"
            f"{image.suffix}"
        )

        temp_path = folder / temp_name

        image.rename(temp_path)

        temporary_files.append(
            (image, temp_path)
        )

    # --------------------------------------------------------
    # 第二階段：
    # 正式命名
    # --------------------------------------------------------

    for index, (old_path, temp_path) in enumerate(
        temporary_files,
        start=start_number
    ):

        # 固定 3 位數
        serial_number = f"{index:03d}"

        # 使用 "-" 作為串接符號
        new_name = (
            f"{prefix}-{serial_number}"
            f"{old_path.suffix}"
        )

        new_path = folder / new_name

        temp_path.rename(new_path)

        print(
            f"{old_path.name}"
            f" -> "
            f"{new_name}"
        )


# ============================================================
# 主程式
# ============================================================

def main():

    print("=" * 70)
    print("圖片批次重新命名工具")
    print("Pure Python / Standard Library Only")
    print("=" * 70)

    # --------------------------------------------------------
    # 使用 .py 程式所在的資料夾
    # --------------------------------------------------------

    folder = Path(__file__).resolve().parent

    print()
    print(f"圖片資料夾：{folder}")

    # --------------------------------------------------------
    # 輸入 prefix
    # --------------------------------------------------------

    prefix = input(
        "\n請輸入檔名前綴（例如 openrouter-applies）："
    ).strip()

    if not prefix:
        print("錯誤：檔名前綴不可為空。")
        return

    # --------------------------------------------------------
    # 找出下一個編號
    # --------------------------------------------------------

    next_number = get_next_serial_number(
        folder,
        prefix
    )

    print()
    print(f"目前下一個可用編號：{next_number:03d}")

    # --------------------------------------------------------
    # 找出尚未處理的圖片
    # --------------------------------------------------------

    images = get_images(
        folder,
        prefix
    )

    if not images:
        print()
        print("找不到需要重新命名的圖片。")
        return

    print()
    print(f"找到 {len(images)} 張尚未處理的圖片")

    # --------------------------------------------------------
    # 預覽
    # --------------------------------------------------------

    print()
    print("重新命名預覽：")
    print("-" * 70)

    for offset, image in enumerate(images):

        number = next_number + offset

        serial_number = f"{number:03d}"

        new_name = (
            f"{prefix}-{serial_number}"
            f"{image.suffix}"
        )

        file_time = datetime.fromtimestamp(
            image.stat().st_mtime
        )

        print(
            f"{serial_number}. "
            f"{image.name}"
            f" -> "
            f"{new_name}"
            f" "
            f"[{file_time:%Y-%m-%d %H:%M:%S}]"
        )

    print("-" * 70)

    # --------------------------------------------------------
    # 確認
    # --------------------------------------------------------

    answer = input(
        "\n確定要重新命名嗎？[y/N]："
    ).strip().lower()

    if answer not in ("y", "yes"):
        print("已取消操作。")
        return

    # --------------------------------------------------------
    # 執行
    # --------------------------------------------------------

    try:

        rename_images(
            folder,
            images,
            prefix,
            next_number
        )

        print()
        print("=" * 70)
        print("重新命名完成！")
        print(f"共處理 {len(images)} 張圖片")
        print(f"輸出位置：{folder}")
        print("=" * 70)

    except Exception as error:

        print()
        print("=" * 70)
        print("重新命名時發生錯誤：")
        print(error)
        print("=" * 70)


if __name__ == "__main__":
    main()
