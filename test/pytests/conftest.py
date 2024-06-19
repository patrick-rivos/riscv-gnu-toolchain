import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--github-token",
        action="store",
        type=str,
        help="Github token value for github api testing"
    )

@pytest.fixture
def github_token(request):
    return request.config.getoption("--github-token")

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "github_token_required: Mark test as requiring the github token"
    )

def pytest_collection_modifyitems(config, items):
    if config.getoption("--github-token"):
        # If the option is set, do nothing (run all tests)
        return
    # skip github token required tests if github token isn't specified
    skip_option = pytest.mark.skip(reason="Requires github token")
    for item in items:
        if "github_token_required" in item.keywords:
            item.add_marker(skip_option)