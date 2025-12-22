from drawer.DrawerHelper import _resolve_plantuml_jar


def test_resolve_plantuml_jar_returns_path_or_none():
    # This is a smoke test that should not raise; jar may or may not exist locally
    path = _resolve_plantuml_jar()
    assert path is None or isinstance(path, str)
