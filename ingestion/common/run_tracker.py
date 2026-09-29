"""Context manager that records every ingestion run in ops.ingestion_runs."""
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from ingestion.common import bq
from ingestion.common.logger import get_logger

logger = get_logger("run_tracker")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def track_run(source: str):
    run = {
        "run_id": uuid.uuid4().hex,
        "source": source,
        "status": "running",
        "started_at": _now(),
        "rows_loaded": 0,
        "files_written": 0,
        "bytes_written": 0,
        "target": None,
        "triggered_by": "github_actions" if os.getenv("GITHUB_ACTIONS") else "local",
        "error_message": None,
    }
    start = time.perf_counter()
    logger.info("Run %s started for source '%s'", run["run_id"], source)
    try:
        yield run
        run["status"] = "success"
    except KeyboardInterrupt:
        run["status"] = "cancelled"
        run["error_message"] = "Interrupted by user (Ctrl+C)"
        raise
    except Exception as exc:
        run["status"] = "failed"
        run["error_message"] = str(exc)[:1000]
        raise
    finally:
        run["finished_at"] = _now()
        run["duration_sec"] = round(time.perf_counter() - start, 2)
        logger.info(
            "Run %s | %s | %s rows | %s files | %.1fs",
            run["run_id"], run["status"], run["rows_loaded"], run["files_written"], run["duration_sec"],
        )
        try:
            bq.log_run(run)
        except Exception as log_error:  # logging must never hide the real error
            logger.warning("Could not write run log: %s", log_error)
