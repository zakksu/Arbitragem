.PHONY: setup start stop status restart open test

setup:
	python scripts/dev.py setup

start:
	python scripts/dev.py start --wait

stop:
	python scripts/dev.py stop

status:
	python scripts/dev.py status

restart:
	python scripts/dev.py restart --wait

open:
	python scripts/dev.py open

test:
	pytest -v
