"""``tacit-qda``: start the interface with the current directory as the workspace.

Frameworks, analyses and lexicons are read from and written to the directory the
command is run in; the shipped frameworks are copied there on first use. Any
further arguments are passed to ``streamlit run`` (for example ``--server.port``).
"""
import os
import subprocess
import sys


def main(argv=None):
    import tacit_qda

    argv = sys.argv[1:] if argv is None else list(argv)
    workdir = os.getcwd()
    copied = tacit_qda.init_workspace(workdir)
    if copied:
        print(f"Copied {len(copied)} shipped frameworks into "
              f"{os.path.join(workdir, 'frameworks')}")
    app = os.path.join(tacit_qda.PACKAGE_DIR, "app.py")
    # 只綁本機位址；使用者要開放給區網時，後面的引數會覆蓋它。
    cmd = [sys.executable, "-m", "streamlit", "run", app,
           "--browser.gatherUsageStats", "false",
           "--server.address", "localhost", *argv]
    return subprocess.call(cmd, cwd=workdir)


if __name__ == "__main__":
    sys.exit(main())
