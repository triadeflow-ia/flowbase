# Worker RQ: processa jobs em background (roda em processo separado do FastAPI)
# Comando: python -m app.worker
import os
import sys
from pathlib import Path

# Garante que o backend está no path e carrega .env
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

from app.config import REDIS_URL


def run_worker():
    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue("default", connection=redis_conn)
    # SimpleWorker no Windows (RQ usa os.fork() que não existe no Windows)
    worker = SimpleWorker([queue], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run_worker()
