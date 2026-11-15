import os

# Tests must never open the real chat database (a running server may hold it locked).
os.environ["SESSION_DB"] = ":memory:"
