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

demo:
	$(PY) -m sautiledger.demo

bench:
	$(PY) -m bench.run --confirm

bench-dry:
	$(PY) -m bench.run --fake

test-live:
	$(PY) -m pytest -m live -q

convert:
	$(PY) -m bench.convert_clips

.PHONY: test chat run demo bench bench-dry test-live
