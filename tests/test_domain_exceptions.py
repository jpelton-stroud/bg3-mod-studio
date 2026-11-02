#!/usr/bin/env python3
"""
test_domain_exceptions.py
-------------------------
Contract unit tests verifying the domain exception hierarchy, inheritance
relationships, standard library compatibility, and chained exception propagation.
"""

from __future__ import annotations

import unittest

import bg3_authoring
import bg3_core
import bg3_theorycraft
from bg3_authoring.exceptions import (
    BG3AuthoringError,
    BG3ConflictError,
    BG3ScaffoldError,
)
from bg3_core.cli.common import NonInteractiveConfirmationError
from bg3_core.exceptions import (
    BG3BinaryError,
    BG3CatalogError,
    BG3EnvironmentError,
    BG3Error,
    BG3PackagingError,
    BG3ProfileError,
)
from bg3_core.modio.modio_client import ModioError
from bg3_theorycraft.exceptions import (
    BG3BuildValidationError,
    BG3SimulationError,
    BG3TheorycraftError,
)


class TestDomainExceptions(unittest.TestCase):
    def test_core_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(BG3Error, Exception))

        # Binary errors inherit BG3Error and ValueError
        self.assertTrue(issubclass(BG3BinaryError, BG3Error))
        self.assertTrue(issubclass(BG3BinaryError, ValueError))

        # Packaging errors inherit BG3Error and RuntimeError
        self.assertTrue(issubclass(BG3PackagingError, BG3Error))
        self.assertTrue(issubclass(BG3PackagingError, RuntimeError))

        # Profile errors inherit BG3Error and RuntimeError
        self.assertTrue(issubclass(BG3ProfileError, BG3Error))
        self.assertTrue(issubclass(BG3ProfileError, RuntimeError))

        # Catalog errors inherit BG3Error and RuntimeError
        self.assertTrue(issubclass(BG3CatalogError, BG3Error))
        self.assertTrue(issubclass(BG3CatalogError, RuntimeError))

        # Environment errors inherit BG3Error and OSError
        self.assertTrue(issubclass(BG3EnvironmentError, BG3Error))
        self.assertTrue(issubclass(BG3EnvironmentError, OSError))

        # CLI errors inherit BG3Error
        self.assertTrue(issubclass(NonInteractiveConfirmationError, BG3Error))

        # ModioError inherits BG3CatalogError
        self.assertTrue(issubclass(ModioError, BG3CatalogError))
        self.assertTrue(issubclass(ModioError, BG3Error))
        self.assertTrue(issubclass(ModioError, RuntimeError))

    def test_authoring_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(BG3AuthoringError, BG3Error))
        self.assertTrue(issubclass(BG3ScaffoldError, BG3AuthoringError))
        self.assertTrue(issubclass(BG3ConflictError, BG3AuthoringError))

    def test_theorycraft_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(BG3TheorycraftError, BG3Error))
        self.assertTrue(issubclass(BG3BuildValidationError, BG3TheorycraftError))
        self.assertTrue(issubclass(BG3SimulationError, BG3TheorycraftError))

    def test_dual_inheritance_catching(self) -> None:
        # BG3BinaryError catchable as BG3Error and ValueError
        err = BG3BinaryError("Corrupted LSPK header")
        with self.assertRaises(BG3Error):
            raise err
        with self.assertRaises(ValueError):
            raise err

        # BG3PackagingError catchable as BG3Error and RuntimeError
        pack_err = BG3PackagingError("Missing manifest")
        with self.assertRaises(BG3Error):
            raise pack_err
        with self.assertRaises(RuntimeError):
            raise pack_err

        # BG3EnvironmentError catchable as BG3Error and OSError
        env_err = BG3EnvironmentError("Larian profile directory not found")
        with self.assertRaises(BG3Error):
            raise env_err
        with self.assertRaises(OSError):
            raise env_err

    def test_exception_chaining(self) -> None:
        cause = OSError("Disk read failure")
        try:
            try:
                raise cause
            except OSError as exc:
                raise BG3BinaryError("Failed reading file") from exc
        except BG3BinaryError as wrapped:
            self.assertIs(wrapped.__cause__, cause)
            self.assertEqual(str(wrapped), "Failed reading file")

    def test_modio_error_attributes_and_chaining(self) -> None:
        err = ModioError("Rate limit exceeded", status_code=429, response_body='{"error": "too many requests"}')
        self.assertEqual(err.status_code, 429)
        self.assertEqual(err.response_body, '{"error": "too many requests"}')
        self.assertIn("Rate limit exceeded", str(err))

    def test_package_facade_reexports(self) -> None:
        for symbol in (
            "BG3Error",
            "BG3BinaryError",
            "BG3PackagingError",
            "BG3ProfileError",
            "BG3CatalogError",
            "BG3EnvironmentError",
        ):
            self.assertIn(symbol, bg3_core.__all__)
            self.assertTrue(hasattr(bg3_core, symbol))

        for symbol in (
            "BG3AuthoringError",
            "BG3ScaffoldError",
            "BG3ConflictError",
        ):
            self.assertIn(symbol, bg3_authoring.__all__)
            self.assertTrue(hasattr(bg3_authoring, symbol))

        for symbol in (
            "BG3TheorycraftError",
            "BG3BuildValidationError",
            "BG3SimulationError",
        ):
            self.assertIn(symbol, bg3_theorycraft.__all__)
            self.assertTrue(hasattr(bg3_theorycraft, symbol))


if __name__ == "__main__":
    unittest.main()
