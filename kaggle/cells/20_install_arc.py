# From Daniel Franzen's ARC-AGI-3 Milestone 2 notebook (Apache-2.0); wheel path resolved per mount layout.
# Install the ARC runtime from the bundled competition wheels.
# Quiet: stdout is discarded; stderr (and a non-zero exit) still surface real failures.
subprocess.check_call(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--no-index",
        "--no-warn-conflicts",
        "--disable-pip-version-check",
        "--find-links",
        str(COMPETITION_DIR / "arc_agi_3_wheels"),   # either mount layout (00_env)
        "arc-agi",
    ],
    stdout=subprocess.DEVNULL,
)