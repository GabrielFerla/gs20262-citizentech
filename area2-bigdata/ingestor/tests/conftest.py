import pytest
from apoio_ingestor import RepoMemoria


@pytest.fixture
def repo() -> RepoMemoria:
    return RepoMemoria()
