import runpy

# `from app.ui import *` only executes app/ui.py's top-level code (all the
# st.* calls that build the page) the very first time Python imports the
# module. Streamlit reruns main.py on every widget interaction (including
# merely selecting a file, before any button is pressed), but Python's
# module cache (sys.modules) means a plain `import` is a no-op on every
# subsequent rerun: no widgets get redrawn, so the page renders blank.
#
# runpy.run_module executes app/ui.py's body in a fresh namespace on every
# call, ignoring the sys.modules cache, so the full page is rebuilt on every
# rerun as Streamlit's execution model requires.
runpy.run_module("app.ui", run_name="__main__")
