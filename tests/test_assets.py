from pathlib import Path
import xml.etree.ElementTree as ET

from matrisk.data import find_project_root


def test_all_local_svg_assets_are_valid_and_manifested():
    root=find_project_root()
    assets=root/"assets"
    svg_files=list(assets.rglob("*.svg"))
    assert len(svg_files)==11
    for path in svg_files:
        ET.parse(path)
    manifest=(assets/"ASSET_MANIFEST.md").read_text(encoding="utf-8")
    for path in svg_files:
        assert path.relative_to(assets).as_posix() in manifest


def test_sidebar_keeps_seven_page_navigation_without_data_snapshot_block():
    root=find_project_root()
    source=(root/"app.py").read_text(encoding="utf-8")
    assert 'page = st.radio("Navigation", PAGES' in source
    assert '"Data Quality & Runs"' in source
    assert 'st.caption("DATA SNAPSHOT")' not in source
    assert 'of {len(DATASETS)} source files present' not in source
    assert 'Availability does not imply scientific validity.' not in source
