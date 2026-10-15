"""Run FaeHub tests against disposable SQLite only, never the school database."""
import os
import sys
import tempfile
import unittest
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    with tempfile.TemporaryDirectory(prefix='faehub-tests-') as directory:
        os.environ.update(FAEHUB_DATABASE_URL='', DATABASE_URL='', RENDER='',
                          FAEHUB_DATABASE=str(Path(directory) / 'tests.db'),
                          FAEHUB_SECRET_KEY='isolated-test-suite-only')
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(sys.argv[1:]) if len(sys.argv) > 1 else loader.discover(str(root), pattern='test_*.py')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
