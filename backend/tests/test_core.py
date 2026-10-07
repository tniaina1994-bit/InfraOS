def test_detect_import():
    from infraos.detect import detect_virt, is_container
    v = detect_virt()
    assert isinstance(v, str)

def test_os_info():
    from infraos.system import os_info
    i = os_info()
    assert "hostname" in i
