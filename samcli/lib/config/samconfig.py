"""
Class representing the samconfig.toml
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Dict, Optional

from samcli.lib.config.exceptions import SamConfigVersionException
from samcli.lib.config.version import VERSION_KEY

LOG = logging.getLogger(__name__)

DEFAULT_ENV = "default"
DEFAULT_GLOBAL_CMDNAME = "global"


class AbstractSamConfig(ABC):

    _filepath: Path
    _document: Optional[Dict]

    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._document = None

    def exists(self):
        return self._filepath.exists()

    def get_all(self, cmd_names, section, env=DEFAULT_ENV):
        """
        Gets a value from the configuration file for the given environment, command and section

        Parameters
        ----------
        cmd_names : list(str)
            List of representing the entire command. Ex: ["local", "generate-event", "s3", "put"]
        section : str
            Specific section within the command to look into. e.g. `parameters`
        env : str
            Optional, Name of the environment

        Returns
        -------
        dict
            Dictionary of configuration options in the file. None, if the config doesn't exist.

        Raises
        ------
        KeyError
            If the config file does *not* have the specific section

        tomlkit.exceptions.TOMLKitError
            If the configuration file is invalid
        """

        env = env or DEFAULT_ENV

        self._read()
        if isinstance(self._document, dict):
            env_content = self._document.get(env, {})
            params = env_content.get(self._to_key(cmd_names), {}).get(section, {})
            if DEFAULT_GLOBAL_CMDNAME in env_content:
                global_params = env_content.get(DEFAULT_GLOBAL_CMDNAME, {}).get(section, {})
                global_params.update(params.copy())
                params = global_params.copy()
            return params
        return {}

    def flush(self):
        """
        Write the data back to file

        Raises
        ------
        tomlkit.exceptions.TOMLKitError
            If the data is invalid

        """
        self._write()

    def path(self):
        return str(self._filepath)

    def put(self, cmd_names, section, key, value, env=DEFAULT_ENV):
        """
        Writes the `key=value` under the given section. You have to call the `flush()` method after `put()` in
        order to write the values back to the config file. Otherwise they will be just saved in-memory, available
        for future access, but never saved back to the file.

        Parameters
        ----------
        cmd_names : list(str)
            List of representing the entire command. Ex: ["local", "generate-event", "s3", "put"]
        section : str
            Specific section within the command to look into. e.g. `parameters`
        key : str
            Key to write the data under
        value : Any
            Value to write. Could be any of the supported TOML types.
        env : str
            Optional, Name of the environment

        Raises
        ------
        tomlkit.exceptions.TOMLKitError
            If the data is invalid
        """

        if not self._document:
            self._read()
        # Empty document prepare the initial structure.
        # self._document is a nested dict, we need to check each layer and add new tables, otherwise duplicated key
        # in parent layer will override the whole child layer
        cmd_name_key = self._to_key(cmd_names)
        env_content = self._document.get(env, {})
        cmd_content = env_content.get(cmd_name_key, {})
        param_content = cmd_content.get(section, {})
        if param_content:
            param_content.update({key: value})
        elif cmd_content:
            cmd_content.update({section: {key: value}})
        elif env_content:
            env_content.update({cmd_name_key: {section: {key: value}}})
        else:
            self._document.update({env: {cmd_name_key: {section: {key: value}}}})
        # If the value we want to add to samconfig already exist in global section, we don't put it again in
        # the special command section
        self._deduplicate_global_parameters(cmd_name_key, section, key, env)

    def sanity_check(self):
        """
        Sanity check the contents of samconfig
        """
        try:
            self._read()
        except SamConfigVersionException as ex:
            raise ex
        except Exception as ex:
            LOG.debug("Invalid configuration file contents", exc_info=ex)
            return False
        else:
            return True

    def get_stage_configuration_names(self):
        self._read()
        if isinstance(self._document, dict):
            return [stage for stage, value in self._document.items() if isinstance(value, dict)]
        return []

    def _ensure_exists(self):
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        self._filepath.touch()

    def version(self):
        return (self._document or dict).get(VERSION_KEY, None)

    def _deduplicate_global_parameters(self, cmd_name_key, section, key, env=DEFAULT_ENV):
        """
        In case the global parameters contains the same key-value pair with command parameters,
        we only keep the entry in global parameters

        Parameters
        ----------
        cmd_name_key : str
            key of command name

        section : str
            Specific section within the command to look into. e.g. `parameters`

        key : str
            Key to write the data under

        env : str
            Optional, Name of the environment
        """
        global_params = self._document.get(env, {}).get(DEFAULT_GLOBAL_CMDNAME, {}).get(section, {})
        command_params = self._document.get(env, {}).get(cmd_name_key, {}).get(section, {})
        if (
            cmd_name_key != DEFAULT_GLOBAL_CMDNAME
            and global_params
            and command_params
            and global_params.get(key)
            and global_params.get(key) == command_params.get(key)
        ):
            value = command_params.get(key)
            save_global_message = (
                f'\n\tParameter "{key}={value}" in [{env}.{cmd_name_key}.{section}] is defined as a global '
                f"parameter [{env}.{DEFAULT_GLOBAL_CMDNAME}.{section}].\n\tThis parameter will be only saved "
                f"under [{env}.{DEFAULT_GLOBAL_CMDNAME}.{section}] in {self._filepath}."
            )
            LOG.info(save_global_message)
            # Only keep the global parameter
            del self._document[env][cmd_name_key][section][key]

    @staticmethod
    def _version_sanity_check(version: Any) -> None:
        if not isinstance(version, float):
            raise SamConfigVersionException(f"'{VERSION_KEY}' key is not present or is in unrecognized format. ")

    @staticmethod
    def _to_key(cmd_names: Iterable[str]) -> str:
        # construct a parsed name that is of the format: a_b_c_d
        return "_".join([cmd.replace("-", "_").replace(" ", "_") for cmd in cmd_names])

    @staticmethod
    def config_dir(template_file_path=None):
        """
        SAM Config file is always relative to the SAM Template. If it the template is not
        given, then it is relative to cwd()
        """
        if template_file_path:
            return os.path.dirname(template_file_path)

        return os.getcwd()

    @abstractmethod
    def _read(self):
        pass

    @abstractmethod
    def _write(self):
        pass
