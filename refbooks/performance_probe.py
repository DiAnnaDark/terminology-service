"""Opt-in local diagnostics. Run explicitly; not part of normal CI test discovery.

    python manage.py test refbooks.performance_probe -v 2

Uses Django's temporary test database; never benchmarks or modifies db.sqlite3.
Timings and memory are observations, not pass/fail performance guarantees.
"""

import statistics
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from django.db import close_old_connections
from django.test import Client, TransactionTestCase

from refbooks.models import Refbook, RefbookElement, RefbookVersion


class PerformanceProbe(TransactionTestCase):
    def populate_to(self, count):
        previous = Refbook.objects.count()
        Refbook.objects.bulk_create(
            [
                Refbook(code=f"PERF-{i}", name=f"Справочник {i}")
                for i in range(previous, count)
            ],
            batch_size=500,
        )
        books = list(Refbook.objects.filter(code__startswith="PERF-"))
        existing = set(
            RefbookVersion.objects.filter(refbook__in=books).values_list(
                "refbook_id", flat=True
            )
        )
        RefbookVersion.objects.bulk_create(
            [
                RefbookVersion(
                    refbook=book, version="1.0", effective_date=date(2022, 1, 1)
                )
                for book in books if book.pk not in existing
            ],
            batch_size=500,
        )
        versions = RefbookVersion.objects.filter(refbook__in=books)
        existing_versions = set(
            RefbookElement.objects.filter(version__in=versions).values_list(
                "version_id", flat=True
            )
        )
        RefbookElement.objects.bulk_create(
            [
                RefbookElement(version=v, code="1", value="Врач-терапевт")
                for v in versions if v.pk not in existing_versions
            ],
            batch_size=500,
        )

    @staticmethod
    def request():
        response = Client().get("/refbooks/")
        if response.status_code != 200:
            raise AssertionError(f"API returned HTTP {response.status_code}")
        return len(response.json()["refbooks"])

    def test_local_measurements(self):
        for size in (100, 1000, 5000):
            self.populate_to(size)
            times = []
            tracemalloc.start()
            for _ in range(3):
                started = time.perf_counter()
                count = self.request()
                times.append((time.perf_counter() - started) * 1000)
                self.assertEqual(count, size)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(
                f"API list: {size} records, median={statistics.median(times):.2f} ms, "
                f"tracemalloc peak={peak / 1024 / 1024:.2f} MiB",
                flush=True,
            )
        # Concurrent READ requests only. This is not a load test of concurrent writes.
        def worker(_):
            close_old_connections()
            try:
                return self.request()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(worker, range(12)))
        self.assertEqual(results, [5000] * 12)
        print("Concurrent API reads: 12/12 returned 5000 records", flush=True)
