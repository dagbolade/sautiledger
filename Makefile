# On Windows without make, use the direct commands from README.md:
#   python -m pytest -q          (= make test)
#   python -m sautiledger.chat   (= make chat)
PY ?= python

test:
	$(PY) -m pytest -q

chat:
	$(PY) -m sautiledger.chat

# `make run` serves the FastAPI app from phase 3 onward; until then it
# opens the chat REPL so the target always does something useful.
run:
	$(PY) -m sautiledger.chat

.PHONY: test chat run
