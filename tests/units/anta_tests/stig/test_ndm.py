# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Tests for anta.tests.stig.ndm."""

from __future__ import annotations

from typing import TYPE_CHECKING

from anta.result_manager.models import AntaTestStatus
from anta.tests.stig.ndm import VerifySSHFIPSRestrictions
from tests.units.anta_tests import test  # noqa: F401

if TYPE_CHECKING:
    from tests.units.anta_tests import AntaUnitTestData

DATA: AntaUnitTestData = {
    (VerifySSHFIPSRestrictions, "success"): {
        "eos_data": ["SSHD status for Default VRF is enabled\nSSH connection limit is 50\nSSH per host connection limit is 20\nFIPS status: enabled\n\n"],
        "expected": {"result": AntaTestStatus.SUCCESS},
    },
    (VerifySSHFIPSRestrictions, "failure-fips-disabled"): {
        "eos_data": ["SSHD status for Default VRF is enabled\nSSH connection limit is 50\nSSH per host connection limit is 20\nFIPS status: disabled\n\n"],
        "expected": {
            "result": AntaTestStatus.FAILURE,
            "messages": ["FIPS restrictions not enabled in management SSH - FIPS status: disabled"],
        },
    },
    (VerifySSHFIPSRestrictions, "failure-fips-line-missing"): {
        "eos_data": ["SSHD status for Default VRF is enabled\nSSH connection limit is 50\nSSH per host connection limit is 20\n\n"],
        "expected": {
            "result": AntaTestStatus.FAILURE,
            "messages": ["FIPS status not found in 'show management ssh' output"],
        },
    },
}
