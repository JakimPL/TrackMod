from importlib import metadata
from typing import Final

from trackmod.spec.text import ENCODING

APPLICATION_NAME: Final = "TrackMod"
PACKAGE_NAME: Final = "trackmod"

APPLICATION_VERSION: Final = metadata.version(PACKAGE_NAME)
APPLICATION_SIGNATURE: Final = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"

APPLICATION_TAG: Final = b"TMOD"
APPLICATION_MARK: Final = APPLICATION_NAME.encode(ENCODING)
