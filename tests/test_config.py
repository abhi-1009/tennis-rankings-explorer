"""Settings must handle special characters in passwords and the Aiven SSL certificate path."""
import importlib

import pytest

import api.config as config_module

ROOT = config_module.PROJECT_ROOT


@pytest.fixture
def make_config(monkeypatch):
    """Reload api.config with the given environment, then restore the real settings afterwards."""
    def build(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(config_module)
    yield build
    monkeypatch.undo()
    importlib.reload(config_module)


def test_password_with_special_characters_is_kept_intact(make_config):
    cfg = make_config(DB_HOST="db.example.com", DB_PORT="28785", DB_USER="avnadmin", DB_PASSWORD="p@ss:w/rd#1", DB_NAME="tennis_db")
    assert cfg.DB_URL.host == "db.example.com"
    assert cfg.DB_URL.port == 28785
    assert cfg.DB_URL.password == "p@ss:w/rd#1"
    assert "p@ss:w/rd#1" not in cfg.DB_URL.render_as_string(hide_password=False).split("@", 1)[1]


def test_relative_ssl_path_is_resolved_from_the_project_root(make_config):
    cfg = make_config(DB_SSL_CA="certs/ca.pem")
    assert cfg.DB_CONNECT_ARGS == {"ssl": {"ca": str(ROOT / "certs" / "ca.pem")}}


def test_no_ssl_arguments_for_local_mysql(make_config):
    cfg = make_config(DB_SSL_CA="")
    assert cfg.DB_CONNECT_ARGS == {}


def test_all_three_endpoints_are_configured():
    assert set(config_module.ENDPOINTS) == {"competitions", "complexes", "doubles_rankings"}
    assert config_module.BASE_URL.startswith("https://api.sportradar.com/tennis/")
