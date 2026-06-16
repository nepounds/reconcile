import reconcile


def test_package_imports() -> None:
    assert reconcile is not None


def test_package_version_exists() -> None:
    assert isinstance(reconcile.__version__, str)
