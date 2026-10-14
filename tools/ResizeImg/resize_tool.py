#!/usr/bin/env python3
"""等比例縮放目前目錄中的圖片，並將原圖移至備份資料夾。"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageOps, UnidentifiedImageError


PRESETS: tuple[tuple[int, int], ...] = (
    (1920, 1080),
    (1600, 1200),
    (1280, 720),
    (1024, 768),
    (800, 600),
)
SUPPORTED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
OUTPUT_STEM_PATTERN = re.compile(r"_\d+x\d+$")
SIZE_PATTERN = re.compile(r"^\s*(\d+)\s*[xX×]\s*(\d+)\s*$")
BACKUP_DIRECTORY = "originals"


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    size_bytes: int


@dataclass(frozen=True)
class ScanResult:
    images: tuple[ImageInfo, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ProcessSummary:
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0


def parse_size(value: str) -> tuple[int, int]:
    """將 WIDTHxHEIGHT 字串轉為正整數尺寸。"""
    match = SIZE_PATTERN.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError("尺寸格式必須為 WIDTHxHEIGHT，例如 1024x768")

    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("寬與高必須大於 0")
    return width, height


def _oriented_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        orientation = image.getexif().get(274)
        width, height = image.size
        if orientation in {5, 6, 7, 8}:
            return height, width
        return width, height


def scan_images(directory: Path) -> ScanResult:
    """掃描目錄頂層可處理且尚未產生尺寸字尾的圖片。"""
    images: list[ImageInfo] = []
    errors: list[str] = []

    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if (
            not path.is_file()
            or path.suffix.lower() not in SUPPORTED_SUFFIXES
            or OUTPUT_STEM_PATTERN.search(path.stem)
        ):
            continue
        try:
            width, height = _oriented_size(path)
            images.append(ImageInfo(path, width, height, path.stat().st_size))
        except (OSError, UnidentifiedImageError) as error:
            errors.append(f"{path.name}: 無法讀取圖片（{error}）")

    return ScanResult(tuple(images), tuple(errors))


def resized_dimensions(
    source: tuple[int, int], target: tuple[int, int]
) -> tuple[int, int]:
    """計算完整縮入目標框且不放大的實際尺寸。"""
    source_width, source_height = source
    target_width, target_height = target
    scale = min(target_width / source_width, target_height / source_height, 1.0)
    return (
        max(1, round(source_width * scale)),
        max(1, round(source_height * scale)),
    )


def estimate_average(
    images: Sequence[ImageInfo], target: tuple[int, int]
) -> tuple[int, float]:
    """以平均原始大小乘平均像素比例，粗估單張輸出大小與變化率。"""
    if not images:
        return 0, 0.0

    average_bytes = sum(image.size_bytes for image in images) / len(images)
    ratios = []
    for image in images:
        output_width, output_height = resized_dimensions(
            (image.width, image.height), target
        )
        ratios.append(
            (output_width * output_height) / (image.width * image.height)
        )

    average_ratio = sum(ratios) / len(ratios)
    return round(average_bytes * average_ratio), (average_ratio - 1.0) * 100


def format_estimate(images: Sequence[ImageInfo], target: tuple[int, int]) -> str:
    estimated_bytes, change_percent = estimate_average(images, target)
    estimated_kib = max(1, round(estimated_bytes / 1024))
    rounded_change = round(change_percent)
    change_text = f"{rounded_change:+d}%" if rounded_change else "0%"
    return (
        f"{target[0]}x{target[1]} / "
        f"≈ {estimated_kib} KB / ≈ {change_text}"
    )


def choose_size(images: Sequence[ImageInfo]) -> tuple[int, int]:
    print("請選擇圖片尺寸上限（檔案大小為粗略估算）：")
    for index, preset in enumerate(PRESETS, start=1):
        print(f"  {index}. {format_estimate(images, preset)}")

    try:
        choice = input("請輸入選項編號：").strip()
        selected = int(choice)
    except (EOFError, ValueError) as error:
        raise ValueError("請輸入有效的選項編號") from error

    if selected not in range(1, len(PRESETS) + 1):
        raise ValueError(f"選項必須介於 1 到 {len(PRESETS)}")
    return PRESETS[selected - 1]


def _save_image(image: Image.Image, destination: Path, suffix: str) -> None:
    suffix = suffix.lower()
    format_name = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }[suffix]

    save_options: dict[str, object] = {}
    icc_profile = image.info.get("icc_profile")
    if icc_profile:
        save_options["icc_profile"] = icc_profile

    exif = image.getexif()
    if exif:
        save_options["exif"] = exif.tobytes()

    if format_name == "JPEG":
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        save_options.update(quality=85, optimize=True)
    elif format_name == "PNG":
        save_options["optimize"] = True
    else:
        save_options.update(quality=85, method=6)

    image.save(destination, format=format_name, **save_options)


def process_image(
    image_info: ImageInfo,
    target: tuple[int, int],
    backup_directory: Path,
) -> tuple[str, str]:
    """處理單張圖片，回傳狀態與顯示訊息。"""
    source = image_info.path
    output_size = resized_dimensions((image_info.width, image_info.height), target)
    output = source.with_name(
        f"{source.stem}_{output_size[0]}x{output_size[1]}{source.suffix}"
    )
    backup = backup_directory / source.name

    if output.exists():
        return "skipped", f"{source.name}: 輸出檔已存在（{output.name}）"
    if backup.exists():
        return "skipped", f"{source.name}: 備份檔已存在（{backup}）"

    temporary_path: Path | None = None
    try:
        with Image.open(source) as opened:
            opened.load()
            transformed = ImageOps.exif_transpose(opened)
            transformed.thumbnail(target, Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(
                prefix=f".{source.stem}_",
                suffix=source.suffix,
                dir=source.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            _save_image(transformed, temporary_path, source.suffix)

        backup_directory.mkdir(parents=True, exist_ok=True)
        os.link(temporary_path, output)
        temporary_path.unlink()
        temporary_path = None

        try:
            shutil.move(str(source), str(backup))
        except Exception:
            output.unlink(missing_ok=True)
            raise

        return "succeeded", f"{source.name} → {output.name}"
    except (OSError, ValueError, UnidentifiedImageError) as error:
        return "failed", f"{source.name}: 處理失敗（{error}）"
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def process_images(
    images: Sequence[ImageInfo], target: tuple[int, int], backup_directory: Path
) -> ProcessSummary:
    counts = {"succeeded": 0, "skipped": 0, "failed": 0}
    for image_info in images:
        status, message = process_image(image_info, target, backup_directory)
        counts[status] += 1
        prefix = {"succeeded": "完成", "skipped": "跳過", "failed": "錯誤"}[status]
        print(f"[{prefix}] {message}")
    return ProcessSummary(**counts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="等比例縮放目前目錄中的圖片，並將原圖備份至 originals/"
    )
    parser.add_argument(
        "--size",
        type=parse_size,
        metavar="WIDTHxHEIGHT",
        help="圖片尺寸上限；未提供時進入互動選單",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    directory = Path.cwd()

    try:
        scan_result = scan_images(directory)
    except OSError as error:
        print(f"錯誤：無法掃描目前目錄（{error}）", file=sys.stderr)
        return 1

    for error in scan_result.errors:
        print(f"[錯誤] {error}", file=sys.stderr)

    if not scan_result.images:
        print("找不到可處理的 JPEG、PNG 或 WebP 圖片。", file=sys.stderr)
        return 1

    if arguments.size is None:
        try:
            target = choose_size(scan_result.images)
        except ValueError as error:
            print(f"錯誤：{error}", file=sys.stderr)
            return 2
    else:
        target = arguments.size

    print(f"將 {len(scan_result.images)} 張圖片縮入 {target[0]}x{target[1]}。")
    summary = process_images(
        scan_result.images, target, directory / BACKUP_DIRECTORY
    )
    print(
        "處理結果："
        f"成功 {summary.succeeded}、跳過 {summary.skipped}、失敗 {summary.failed}"
    )

    return 0 if summary.skipped == 0 and summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
