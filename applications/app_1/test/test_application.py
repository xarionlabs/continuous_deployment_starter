from application import get_str

def test_get_str():
    assert get_str() == "This is a shared string from the shared library."
