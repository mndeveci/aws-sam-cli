"""
SamConfig TOML support
"""
from pathlib import Path

import tomlkit

from samcli.lib.config.samconfig import AbstractSamConfig
from samcli.lib.config.version import VERSION_KEY, SAM_CONFIG_VERSION

DEFAULT_CONFIG_FILE_NAME = "samconfig.toml"


class SamConfigToml(AbstractSamConfig):
    """
    Class to interface with `samconfig.toml` file.
    """

    document = None

    def __init__(self, config_dir, filename=None):
        """
        Initialize the class

        Parameters
        ----------
        config_dir : string
            Directory where the configuration file needs to be stored
        filename : string
            Optional. Name of the configuration file. It is recommended to stick with default so in the future we
            could automatically support auto-resolving multiple config files within same directory.
        """
        super().__init__(Path(config_dir, filename or DEFAULT_CONFIG_FILE_NAME))

    def sanity_check(self):
        """
        Sanity check the contents of samconfig
        """
        try:
            self._read()
        except tomlkit.exceptions.TOMLKitError:
            return False
        else:
            return True

    def _read(self):
        if not self._document:
            try:
                txt = self._filepath.read_text()
                self._document = tomlkit.loads(txt)
                self._version_sanity_check(self.version())
            except OSError:
                self._document = tomlkit.document()

        if self._document:
            self._version_sanity_check(self.version())
        return self._document

    def _write(self):
        if not self._document:
            return

        self._ensure_exists()

        current_version = self.version() if self.version() else SAM_CONFIG_VERSION
        try:
            self._document[VERSION_KEY] = current_version
        except tomlkit.exceptions.KeyAlreadyPresent:
            # NOTE(TheSriram): Do not attempt to re-write an existing version
            pass
        self._filepath.write_text(tomlkit.dumps(self._document))
