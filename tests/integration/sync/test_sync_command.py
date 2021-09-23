import json
import shutil
import uuid
from pathlib import Path
from unittest import skipIf

import boto3

from samcli.lib.utils import osutils
from tests.integration.package.package_integ_base import PackageIntegBase
from tests.integration.sync.sync_integ_base import SyncIntegBase
from tests.testing_utils import RUNNING_ON_CI, RUNNING_TEST_FOR_MASTER_ON_CI, RUN_BY_CANARY, run_command

SKIP_SYNC_TESTS = RUNNING_ON_CI and RUNNING_TEST_FOR_MASTER_ON_CI and not RUN_BY_CANARY

@skipIf(SKIP_SYNC_TESTS, "Skip sync tests in CI/CD only")
class TestSync(PackageIntegBase, SyncIntegBase):

    @classmethod
    def setUpClass(cls):
        PackageIntegBase.setUpClass()
        cls.sync_test_path = cls.test_data_path.parent.joinpath("sync")

    def setUp(self):
        super().setUp()
        self.stacks = []
        session = boto3.session.Session()
        self.lambda_client = session.client("lambda")
        self.cfn_client = session.client("cloudformation")

    def tearDown(self):
        for stack in self.stacks:
            self.cfn_client.delete_stack(StackName=stack)
        super().tearDown()

    def test_sync_individual_function(self):
        template_path = self.sync_test_path.joinpath("single-function-template.yaml")
        project_path = self.sync_test_path.joinpath("DynamicPython")
        with osutils.mkdir_temp() as tmp_project_dir:
            # create tmp directory and move project resources there
            tmp_project_path = Path(tmp_project_dir)
            tmp_function_path = tmp_project_path.joinpath("FunctionCode")
            shutil.copyfile(template_path, tmp_project_path.joinpath("template.yml"))
            shutil.copytree(project_path, tmp_function_path)

            # make a change in the function code
            latest_return = str(uuid.uuid4())
            with open(tmp_function_path.joinpath("app.py"), "r+") as function_src:
                function_content = function_src.read()
                function_content = function_content.replace("${result}", latest_return)
                function_src.write(function_content)

            # run the initial sync
            stack_name = f"sync-test-{str(uuid.uuid4())}"
            self.stacks.append(stack_name)
            function_name = f"function-{str(uuid.uuid4())}"
            sync_command_list = self.get_sync_command_list(
                stack_name=stack_name,
                parameter_overrides=f"CodeUri={str(tmp_function_path)} FunctionName={function_name} Runtime=python3.7 Handler=app.handler",
            )
            sync_run = run_command(cwd=tmp_project_path, command_list=sync_command_list)
            self.assertEqual(sync_run.process.returncode, 0)

            # verify function runs as expected
            invoke_result = self.lambda_client.invoke(FunctionName=function_name)
            self.assertEqual(latest_return, json.loads(invoke_result.get("Payload").read()).get("result"))

            # make a change to function code and run sync
            with open(tmp_function_path.joinpath("app.py"), "r+") as function_src:
                function_content = function_src.read()
                function_content = function_content.replace(latest_return, "${result}")
                latest_return = str(uuid.uuid4())
                function_content = function_content.replace("${result}", latest_return)
                function_src.write(function_content)

            sync_command_list = self.get_sync_command_list(
                stack_name=stack_name,
                code=True,
                resource_id="MyFunction",
                parameter_overrides=f"CodeUri={str(tmp_function_path)} FunctionName={function_name} Runtime=python3.7 Handler=app.handler",
            )
            sync_run = run_command(cwd=tmp_project_path, command_list=sync_command_list)
            self.assertEqual(sync_run.process.returncode, 0)

            # verify function returns latest result with this change
            invoke_result = self.lambda_client.invoke(FunctionName=function_name)
            self.assertEqual(latest_return, json.loads(invoke_result.get("Payload").read()).get("result"))







