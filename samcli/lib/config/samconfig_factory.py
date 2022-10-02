"""
SamConfig instance factory
"""
import os
from pathlib import Path

from samcli.lib.config.samconfig import AbstractSamConfig
from samcli.lib.config.samconfig_toml import SamConfigToml, DEFAULT_CONFIG_FILE_NAME as DEFAULT_CONFIG_TOML_FILE_NAME
from samcli.lib.config.samconfig_yaml import SamConfigYaml, DEFAULT_CONFIG_FILE_NAME as DEFAULT_CONFIG_YAML_FILE_NAME


def get_sam_config(config_dir, filename=None) -> AbstractSamConfig:
    if filename:
        if ".toml" in filename:
            return SamConfigToml(config_dir, filename)
        if ".yaml" in filename:
            return SamConfigYaml(config_dir, filename)

    if Path(config_dir).exists():
        files = os.listdir(config_dir)
        if DEFAULT_CONFIG_TOML_FILE_NAME in files:
            return SamConfigToml(config_dir, filename)
        if DEFAULT_CONFIG_YAML_FILE_NAME in files:
            return SamConfigYaml(config_dir, filename)

    return SamConfigYaml(config_dir, filename)
