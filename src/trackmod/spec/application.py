from importlib import metadata
from typing import Final

APPLICATION_NAME: Final = "TrackMod"
PACKAGE_NAME: Final = "trackmod"

APPLICATION_VERSION: Final = metadata.version(PACKAGE_NAME)
APPLICATION_SIGNATURE: Final = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"
