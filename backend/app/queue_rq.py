# Fila RQ: enfileira processamento de jobs (usado pelo FastAPI)
from redis import Redis
from rq import Queue

from app.config import REDIS_URL

_redis = Redis.from_url(REDIS_URL)
queue = Queue("default", connection=_redis)
