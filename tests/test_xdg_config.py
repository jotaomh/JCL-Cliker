import os
import tempfile

from app.config import (
    APP_NAME,
    LEGACY_APP_NAME,
    load_config,
    save_config,
    _config_file,
    _xdg_config_home,
)


def test_config_file_respects_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    expected = tmp_path / "jcl-clicker" / "config.json"
    assert _config_file() == expected


def test_app_name_is_rebranded():
    assert APP_NAME == "jcl-clicker"


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    original = {
        "interval": 0.5,
        "button": 2,
        "amount": 10,
        "hotkey": "f7",
        "theme": "light",
    }
    save_config(original)
    loaded = load_config()
    assert loaded == original


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    loaded = load_config()
    assert loaded["interval"] == 0.1
    assert loaded["hotkey"] == "f6"
    assert _config_file().exists()


def test_migrate_from_repo_root_legacy(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    legacy = tmp_path / "repo_root" / "config.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text('{"interval": 0.3, "button": 3, "amount": 5, "hotkey": "f8"}')

    monkeypatch.setattr(
        "app.config._legacy_config_files",
        lambda: [legacy],
    )
    loaded = load_config()
    assert loaded["interval"] == 0.3
    assert loaded["button"] == 3
    assert _config_file().exists()


def test_migrate_from_previous_install(tmp_path, monkeypatch):
    """Instalação anterior ao rebranding: ~/.config/autoclicker/config.json."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    old_dir = tmp_path / LEGACY_APP_NAME
    old_dir.mkdir(parents=True, exist_ok=True)
    (old_dir / "config.json").write_text(
        '{"interval": 0.25, "button": 2, "amount": 100, "hotkey": "f9"}'
    )

    # sem config legado na raiz do repo, só o da instalação antiga
    monkeypatch.setattr(
        "app.config._legacy_config_files",
        lambda: [_xdg_config_home() / LEGACY_APP_NAME / "config.json"],
    )

    loaded = load_config()
    assert loaded["interval"] == 0.25
    assert loaded["button"] == 2
    assert _config_file() == tmp_path / APP_NAME / "config.json"
    assert _config_file().exists()


def test_migrate_prefers_newest_when_both_exist(tmp_path, monkeypatch):
    """Repo root é mais antigo que ~/.config/autoclicker: este último vence."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    repo_legacy = tmp_path / "repo_root" / "config.json"
    repo_legacy.parent.mkdir(parents=True, exist_ok=True)
    repo_legacy.write_text('{"interval": 0.99}')

    old_install = tmp_path / LEGACY_APP_NAME / "config.json"
    old_install.parent.mkdir(parents=True, exist_ok=True)
    old_install.write_text('{"interval": 0.11}')

    monkeypatch.setattr(
        "app.config._legacy_config_files",
        lambda: [repo_legacy, old_install],
    )
    loaded = load_config()
    assert loaded["interval"] == 0.11


def test_existing_config_is_not_overwritten_by_migration(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({"interval": 0.42})

    legacy = tmp_path / "repo_root" / "config.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text('{"interval": 0.99}')

    monkeypatch.setattr(
        "app.config._legacy_config_files",
        lambda: [legacy],
    )
    loaded = load_config()
    assert loaded["interval"] == 0.42