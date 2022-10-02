"""
SamConfig YAML support
"""
from pathlib import Path
from typing import Optional

from samcli.lib.config.samconfig import AbstractSamConfig
from samcli.lib.config.version import SAM_CONFIG_VERSION, VERSION_KEY
from samcli.yamlhelper import yaml_parse, yaml_dump

DEFAULT_CONFIG_FILE_NAME = "samconfig.yaml"


class SamConfigYaml(AbstractSamConfig):

    _filepath: Path

    def __init__(self, config_dir: str, filename: Optional[str] = None):
        super().__init__(Path(config_dir, filename or DEFAULT_CONFIG_FILE_NAME))

    def _read(self):
        if not self._document:
            try:
                txt = self._filepath.read_text()
                self._document = yaml_parse(txt)
                self._version_sanity_check(self.version())
            except OSError:
                self._document = dict()
        if self._document:
            self._version_sanity_check(self.version())
        return self._document

    def _write(self):
        if not self._document:
            return

        self._ensure_exists()
        current_version = self.version() if self.version() else SAM_CONFIG_VERSION
        self._document[VERSION_KEY] = current_version
        self._filepath.write_text(yaml_dump(self._document))
