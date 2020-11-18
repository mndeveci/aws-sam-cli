"""
Contains information about newer version checker for SAM CLI
"""
import logging
from datetime import datetime, timedelta
from requests import get
from samcli import __version__ as installed_version
from samcli.cli.global_config import GlobalConfig

LOG = logging.getLogger(__name__)

AWS_SAM_CLI_PYPI_ENDPOINT = "https://pypi.org/pypi/aws-sam-cli/json"
AWS_SAM_CLI_INSTALL_DOCS = (
    "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
)
PYPI_CALL_TIMEOUT_IN_SECONDS = 5
DELTA_DAYS = 7


def check_newer_version(func):
    """
    This function returns a wrapped function definition, which checks if there are newer version of SAM CLI available

    Parameters
    ----------
    func: function reference
        Actual function (command) which will be executed

    Returns
    -------
    function reference:
        A wrapped function reference which executes original function and checks newer version of SAM CLI
    """

    def wrapped(*args, **kwargs):
        # execute actual command first
        actual_result = func(*args, **kwargs)

        # run everything else in try-except block
        global_config = None
        need_to_update_last_check_time = True
        try:
            global_config = GlobalConfig()
            last_version_check = global_config.last_version_check

            if is_last_check_older_then_week(last_version_check):
                compare_current_version()
            else:
                need_to_update_last_check_time = False
        except Exception as e:
            LOG.debug("New version check failed", exc_info=e)
        finally:
            if need_to_update_last_check_time:
                update_last_check_time(global_config)

        return actual_result

    return wrapped


def compare_current_version():
    """
    Compare current up to date version with the installed one, and inform if a newer version available
    """
    response = get(AWS_SAM_CLI_PYPI_ENDPOINT, timeout=PYPI_CALL_TIMEOUT_IN_SECONDS)
    result = response.json()
    current_version = result.get("info", {}).get("version", None)
    LOG.debug("Installed version %s, current version %s", installed_version, current_version)
    if current_version and installed_version != current_version:
        LOG.info("There is a newer version available for SAM CLI!")
        LOG.info("New version: %s Your version: %s", current_version, installed_version)
        LOG.info("To download the new version, go here %s", AWS_SAM_CLI_INSTALL_DOCS)


def update_last_check_time(global_config):
    """
    Update last_check_time in GlobalConfig
    Parameters
    ----------
    global_config: GlobalConfig
        GlobalConfig object that have been read
    """
    try:
        if global_config:
            global_config.last_version_check = datetime.utcnow().timestamp()
    except Exception as e:
        LOG.debug("Updating last version check time was failed", exc_info=e)


def is_last_check_older_then_week(last_version_check):
    """
    Check if last version check have been made longer then a week ago

    Parameters
    ----------
    last_version_check: epoch time
        last_version_check epoch time read from GlobalConfig

    Returns
    -------
    bool:
        True if last_version_check is None or older then a week, False otherwise
    """
    if last_version_check is None:
        return True

    epoch_week_ago = datetime.utcnow() - timedelta(days=DELTA_DAYS)
    return last_version_check < epoch_week_ago
