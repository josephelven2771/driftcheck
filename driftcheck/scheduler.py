"""Periodic drift-check scheduler.

Runs drift checks on a configurable interval and emits results to
a pluggable sink (default: stderr).  Designed to be used as a
long-running background process or inside a container side-car.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from driftcheck.comparator import DriftResult

log = logging.getLogger(__name__)

# Sink signature: receives the list of DriftResults produced by one tick.
SinkFn = Callable[[List[DriftResult]], None]


class SchedulerError(Exception):
    """Raised when the scheduler cannot be configured or started."""


@dataclass
class SchedulerConfig:
    """Configuration for the drift-check scheduler."""

    interval_seconds: int = 60
    max_ticks: Optional[int] = None  # None → run forever
    sinks: List[SinkFn] = field(default_factory=list)

    def validate(self) -> None:
        if self.interval_seconds <= 0:
            raise SchedulerError(
                f"interval_seconds must be > 0, got {self.interval_seconds}"
            )
        if self.max_ticks is not None and self.max_ticks < 1:
            raise SchedulerError(
                f"max_ticks must be >= 1 or None, got {self.max_ticks}"
            )


class Scheduler:
    """Runs a *check_fn* periodically and forwards results to registered sinks."""

    def __init__(
        self,
        check_fn: Callable[[], List[DriftResult]],
        config: SchedulerConfig,
    ) -> None:
        config.validate()
        self._check_fn = check_fn
        self._config = config
        self._tick_count = 0
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def stop(self) -> None:
        """Signal the scheduler to stop after the current tick."""
        self._running = False

    def run(self) -> None:
        """Block and run until *max_ticks* reached or :meth:`stop` called."""
        self._running = True
        cfg = self._config

        while self._running:
            self._tick()
            if cfg.max_ticks is not None and self._tick_count >= cfg.max_ticks:
                break
            if self._running:
                time.sleep(cfg.interval_seconds)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        self._tick_count += 1
        log.debug("Scheduler tick #%d", self._tick_count)
        try:
            results = self._check_fn()
        except Exception as exc:  # noqa: BLE001
            log.error("check_fn raised on tick #%d: %s", self._tick_count, exc)
            return
        for sink in self._config.sinks:
            try:
                sink(results)
            except Exception as exc:  # noqa: BLE001
                log.error("Sink %r raised: %s", sink, exc)
