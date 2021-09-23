import os
from unittest import TestCase

from tests.testing_utils import RUN_BY_CANARY, RUNNING_TEST_FOR_MASTER_ON_CI, RUNNING_ON_CI

SKIP_SYNC_TESTS = RUNNING_ON_CI and RUNNING_TEST_FOR_MASTER_ON_CI and not RUN_BY_CANARY


class SyncIntegBase(TestCase):

    def base_command(self):
        command = "sam"
        if os.getenv("SAM_CLI_DEV"):
            command = "samdev"

        return command

    def get_sync_command_list(
            self,
            stack_name,
            code=False,
            resource_id=None,
            parameter_overrides=None,
    ):
        command_list = [self.base_command(), "sync"]

        if code:
            command_list = command_list + ["--code"]

        if stack_name:
            command_list = command_list + ["--stack-name", stack_name]

        if resource_id:
            command_list = command_list + ["--resource-id", resource_id]

        if parameter_overrides:
            command_list = command_list + ["--parameter-overrides", str(parameter_overrides)]

        return command_list