"""TACIT as an installed package (``pip install tacit-qda``).

The modules import one another by their plain names (``import tacit_framework``),
exactly as when they are run from the repository, so importing this package puts
its own directory on ``sys.path``. After that the engines can be used from any
script::

    import tacit_qda
    import tacit_framework as F
    F.FRAMEWORK_DIR = tacit_qda.bundled_frameworks_dir()
    F.activate_by_id("ri_stilgoe_2013")

The application reads and writes frameworks, analyses and lexicons in the working
directory. ``init_workspace`` copies the shipped frameworks there; the
``tacit-qda`` command does so before starting the interface.

Running from the repository (launchers, ``streamlit run src/app.py``, the tests)
does not use this file.
"""
import os
import shutil
import sys

__version__ = "1.1.1"

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)


def bundled_frameworks_dir():
    """Directory holding the shipped framework JSON files."""
    for d in (os.path.join(PACKAGE_DIR, "frameworks"),                    # installed
              os.path.join(os.path.dirname(PACKAGE_DIR), "frameworks")):  # repository
        if os.path.isdir(d):
            return d
    raise FileNotFoundError("the shipped frameworks were not found next to the package")


def init_workspace(path="."):
    """Copy the shipped frameworks into ``path/frameworks``; existing files are kept.

    Returns the file names copied.
    """
    target = os.path.join(path, "frameworks")
    os.makedirs(target, exist_ok=True)
    copied = []
    src = bundled_frameworks_dir()
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".json") and not os.path.exists(os.path.join(target, fn)):
            shutil.copy2(os.path.join(src, fn), os.path.join(target, fn))
            copied.append(fn)
    return copied
