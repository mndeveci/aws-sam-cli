"""
InfraSyncExecutor class which runs build, package and deploy contexts
"""
import logging
import re

from boto3 import Session
from botocore.exceptions import ClientError

from samcli.commands._utils.template import get_template_data
from samcli.commands.build.build_context import BuildContext
from samcli.commands.deploy.deploy_context import DeployContext
from samcli.commands.package.package_context import PackageContext
from samcli.lib.utils.resources import AWS_SERVERLESS_FUNCTION, AWS_LAMBDA_FUNCTION
from samcli.yamlhelper import yaml_parse

LOG = logging.getLogger(__name__)


class InfraSyncExecutor:

    _build_context: BuildContext
    _package_context: PackageContext
    _deploy_context: DeployContext

    def __init__(self, build_context: BuildContext, package_context: PackageContext, deploy_context: DeployContext):
        self._build_context = build_context
        self._package_context = package_context
        self._deploy_context = deploy_context

        session = Session(profile_name=self._deploy_context.profile, region_name=self._deploy_context.region)
        self._cfn_client = session.client("cloudformation")
        self._s3_client = session.client("s3")

    def execute_infra_sync(self) -> bool:
        self._build_context.set_up()
        self._build_context.run()
        self._package_context.run()

        if self._compare_templates(self._package_context.output_template_file, self._deploy_context.stack_name):
            LOG.info("Template haven't been changed since last deployment, skipping infra sync...")
            return False

        self._deploy_context.run()
        return True

    def _compare_templates(self, local_template_path: str, stack_name: str) -> bool:
        if local_template_path.startswith("https://"):
            parsed_s3_location = re.search(r"https:\/\/[^/]*\/([^/]*)\/(.*)", local_template_path)
            s3_bucket = parsed_s3_location.group(1)
            s3_key = parsed_s3_location.group(2)
            s3_object = self._s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            current_template = yaml_parse(s3_object.get('Body').read().decode("utf-8"))
        else:
            current_template = get_template_data(local_template_path)

        try:
            last_deployed_template_str = self._cfn_client.get_template(
                StackName=stack_name, TemplateStage="Original"
            ).get("TemplateBody", "")
        except ClientError as ex:
            LOG.debug("Stack with name %s does not exist", stack_name, exc_info=ex)
            return False

        last_deployed_template_dict = yaml_parse(last_deployed_template_str)

        self._remove_unnecesary_fields(last_deployed_template_dict)
        self._remove_unnecesary_fields(current_template)
        if last_deployed_template_dict != current_template:
            return False

        for resource_logical_id in current_template.get("Resources", []):
            resource_dict = current_template.get("Resources").get(resource_logical_id)
            if resource_dict.get("Type") == "AWS::CloudFormation::Stack":
                stack_resource_detail = self._cfn_client.describe_stack_resource(
                    StackName=stack_name, LogicalResourceId=resource_logical_id
                )

                if not self._compare_templates(
                        resource_dict.get("Properties", {}).get("TemplateURL"),
                        stack_resource_detail.get("StackResourceDetail", {}).get("PhysicalResourceId"),
                ):
                    return False

        return True

    def _remove_unnecesary_fields(self, template_dict: dict):
        resources = template_dict.get("Resources", [])
        for resource_logical_id in resources:
            resource_dict = resources.get(resource_logical_id)
            if resource_dict.get("Type") in [AWS_SERVERLESS_FUNCTION, AWS_LAMBDA_FUNCTION]:
                resource_dict.get("Properties", {}).pop("CodeUri", None)
