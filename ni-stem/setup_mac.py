import distutils
from distutils import core
import os
import shutil

import setup_general

distFolder = "dist_mac"

rootModule = "ni-stem"

# We remove the .py extension from the root script file and make it executable
# The file is then added to the distribution through the manifest
if os.path.exists(rootModule) and os.path.isfile(rootModule):
    os.remove(rootModule)
shutil.copyfile(rootModule + ".py", rootModule)
os.chmod(rootModule, 511)

distutils.core.setup(
        options = {
                "sdist": {
                "dist_dir": distFolder,
                }},
        name = setup_general.name,
        version = setup_general.version,
        description = setup_general.description,
        author = setup_general.author,
        author_email = setup_general.authorEmail,
        url = setup_general.url,
        py_modules = ["_internal"],
        packages = ["mutagen", "mutagen.id3"],
        package_dir = {"mutagen": "mutagen"}
        )

os.remove(rootModule)
