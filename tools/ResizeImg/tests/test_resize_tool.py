from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from resize_tool import (
    ImageInfo,
    estimate_average,
    parse_size,
    process_image,
    resized_dimensions,
    scan_images,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_image(
    path: Path,
    size: tuple[int, int] = (1200, 800),
    mode: str = "RGB",
) -> None:
    color = (30, 120, 220, 128) if mode == "RGBA" else (30, 120, 220)
    Image.new(mode, size, color).save(path)


def test_parse_size_accepts_common_separators() -> None:
    assert parse_size("1024x768") == (1024, 768)
    assert parse_size(" 800 X 600 ") == (800, 600)
    assert parse_size("640×480") == (640, 480)


@pytest.mark.parametrize("value", ["1024", "0x768", "-1x100", "axb"])
def test_parse_size_rejects_invalid_values(value: str) -> None:
    with pytest.raises(Exception):
        parse_size(value)


def test_resized_dimensions_preserves_ratio_without_upscaling() -> None:
    assert resized_dimensions((2000, 1000), (1024, 768)) == (1024, 512)
    assert resized_dimensions((1000, 2000), (1024, 768)) == (384, 768)
    assert resized_dimensions((320, 240), (1024, 768)) == (320, 240)


def test_estimate_uses_average_size_and_average_pixel_ratio(
    tmp_path: Path,
) -> None:
    images = (
        ImageInfo(tmp_path / "a.jpg", 2000, 1000, 200_000),
        ImageInfo(tmp_path / "b.jpg", 1000, 500, 100_000),
    )

    estimated_bytes, change = estimate_average(images, (1000, 500))

    assert estimated_bytes == 93_750
    assert change == pytest.approx(-37.5)


def test_scan_filters_generated_outputs_and_reports_invalid_images(
    tmp_path: Path,
) -> None:
    create_image(tmp_path / "source.jpg")
    create_image(tmp_path / "already_600x400.jpg", (600, 400))
    create_image(tmp_path / "ignored.gif")
    (tmp_path / "broken.png").write_text("not an image")

    result = scan_images(tmp_path)

    assert [image.path.name for image in result.images] == ["source.jpg"]
    assert len(result.errors) == 1
    assert result.errors[0].startswith("broken.png:")


@pytest.mark.parametrize(
    ("source_size", "expected_size"),
    [((1600, 900), (1024, 576)), ((900, 1600), (432, 768))],
)
def test_processes_landscape_and_portrait_images(
    tmp_path: Path,
    source_size: tuple[int, int],
    expected_size: tuple[int, int],
) -> None:
    source = tmp_path / "photo.jpg"
    create_image(source, source_size)
    image_info = scan_images(tmp_path).images[0]

    status, _ = process_image(image_info, (1024, 768), tmp_path / "originals")

    output = tmp_path / f"photo_{expected_size[0]}x{expected_size[1]}.jpg"
    assert status == "succeeded"
    assert not source.exists()
    assert (tmp_path / "originals" / "photo.jpg").is_file()
    with Image.open(output) as image:
        assert image.size == expected_size


def test_transparent_png_is_not_upscaled_and_keeps_alpha(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    create_image(source, (320, 180), mode="RGBA")
    image_info = scan_images(tmp_path).images[0]

    status, _ = process_image(image_info, (1024, 768), tmp_path / "originals")

    assert status == "succeeded"
    with Image.open(tmp_path / "logo_320x180.png") as image:
        assert image.size == (320, 180)
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 128


@pytest.mark.parametrize("collision_location", ["output", "backup"])
def test_existing_destination_is_skipped_without_moving_source(
    tmp_path: Path, collision_location: str
) -> None:
    source = tmp_path / "photo.jpg"
    create_image(source)
    backup_directory = tmp_path / "originals"
    backup_directory.mkdir()
    collision = (
        tmp_path / "photo_1024x683.jpg"
        if collision_location == "output"
        else backup_directory / "photo.jpg"
    )
    collision.write_bytes(b"existing")
    image_info = scan_images(tmp_path).images[0]

    status, _ = process_image(image_info, (1024, 768), backup_directory)

    assert status == "skipped"
    assert source.is_file()
    assert collision.read_bytes() == b"existing"


def test_cli_end_to_end_with_explicit_size(tmp_path: Path) -> None:
    create_image(tmp_path / "sample.webp", (1000, 500))

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "resize_tool.py"),
            "--size",
            "400x400",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "成功 1、跳過 0、失敗 0" in completed.stdout
    assert (tmp_path / "sample_400x200.webp").is_file()
    assert (tmp_path / "originals" / "sample.webp").is_file()
