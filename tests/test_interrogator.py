"""owimetadatabase_soilapi tests"""
from owimetadatabase_soilapi import __version__


def test_version():
    """Test the package version"""
    assert __version__ == "0.1.0"
