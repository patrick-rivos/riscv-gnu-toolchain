from pathlib import Path
import sys

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))
from create_patches_files import get_patch_info


def test_riscv_body():
    # https://patchwork.sourceware.org/project/gcc/patch/20240611061943.698499-1-pan2.li@intel.com/
    # patch with riscv in the body of the message
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&project=6&before=2024-06-11T06:20:00&since=2024-06-11T06:15:00"
    series_name, series_url, download_links, patchworks_links = get_patch_info(url)

    assert len(download_links.items()) == 1
    assert len(patchworks_links.items()) == 1


def test_riscv_title():
    # https://patchwork.sourceware.org/project/gcc/patch/20240701091303.1968994-1-pan2.li@intel.com/
    # patch with riscv in the title
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&project=6&since=2024-07-01T09:10:00&before=2024-07-01T09:15:00"
    series_name, series_url, download_links, patchworks_links = get_patch_info(url)

    assert len(download_links.items()) == 1
    assert len(patchworks_links.items()) == 1


def test_non_riscv():
    # https://patchwork.sourceware.org/project/gcc/patch/20240624135510.3509497-1-pan2.li@intel.com/
    # patch without riscv in the body of the message
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&project=6&since=2024-06-24T13:55:00&before=2024-06-24T14:00:00"
    series_name, series_url, download_links, patchworks_links = get_patch_info(url)

    assert len(download_links.items()) == 0
    assert len(patchworks_links.items()) == 0

def test_no_patches():
    # No patches were sent in this time range
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&project=6&since=2024-06-24T13:50:00&before=2024-06-24T13:51:00"
    _series_name, _series_url, download_links, patchworks_links = get_patch_info(url)

    assert len(download_links) == 0
    assert len(patchworks_links) == 0
