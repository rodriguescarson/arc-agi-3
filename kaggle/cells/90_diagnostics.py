# Verbatim from Daniel Franzen's ARC-AGI-3 Milestone 2 notebook (Apache-2.0).
from html import escape

from IPython.display import HTML, display

diagnostics_html = WORKING_DIR / "diagnostics.html"
if diagnostics_html.is_file():
    display(
        HTML(
            f'<iframe srcdoc="{escape(diagnostics_html.read_text(), quote=True)}" '
            'width="100%" height="900" style="border:0"></iframe>'
        )
    )
else:
    print("No diagnostics.html - minimal diagnostics (real submission) suppresses it.")
