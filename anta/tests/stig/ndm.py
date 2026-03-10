# Copyright (c) 2023-2026 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""STIG-required tests for Arista EOS Network Device Management (NDM)."""

from __future__ import annotations

from typing import ClassVar

from anta.models import AntaCommand, AntaTemplate, AntaTest


class VerifySSHFIPSRestrictions(AntaTest):
    """Verifies that FIPS restrictions are enabled in management SSH.

    STIG Reference: V-255955 (CAT I) - Arista MLS EOS 4.x NDM - 2025-02-20

    Expected Results
    ----------------
    * Success: The ``show management ssh`` output reports ``FIPS status: enabled``.
    * Failure: The FIPS status line is absent or reports ``FIPS status: disabled``.

    Examples
    --------
    ```yaml
    anta.tests.stig.ndm:
      - VerifySSHFIPSRestrictions:
    ```
    """

    categories: ClassVar[list[str]] = ["security", "stig"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show management ssh", ofmt="text")]

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySSHFIPSRestrictions."""
        ssh_output = self.instance_commands[0].text_output
        fips_line = next((line for line in ssh_output.splitlines() if "FIPS status" in line), None)
        if fips_line is None:
            self.result.is_failure("FIPS status not found in 'show management ssh' output")
        elif "enabled" not in fips_line.lower():
            self.result.is_failure(f"FIPS restrictions not enabled in management SSH - {fips_line.strip()}")
        else:
            self.result.is_success()
