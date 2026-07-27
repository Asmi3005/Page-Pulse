import pytest
from httpx import ASGITransport, AsyncClient

from app.cache import clear_cache
from app.main import app
from app.middleware import clear_rate_limits


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    clear_cache()
    clear_rate_limits()
    yield
    clear_cache()
    clear_rate_limits()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
