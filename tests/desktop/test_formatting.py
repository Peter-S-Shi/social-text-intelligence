import pytest

from social_text_intelligence.desktop.formatting import format_bytes

MIB = 1024 * 1024


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 B"),
        (929, "929 B"),
        (1536, "1.5 KB"),
        (502_401_839, "479.1 MB"),  # the sentiment model, as the contract lists it
        (1_004_464_932, "957.9 MB"),  # both models together
        (1000 * MIB, "0.98 GB"),  # 1000 or more switches unit, never "1000.0 MB"
        (3 * 1024 * MIB, "3.00 GB"),
    ],
)
def test_sizes_use_binary_units_with_windows_labels(size: int, expected: str) -> None:
    assert format_bytes(size) == expected
