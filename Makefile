.PHONY: backend frontend run install

install:
	python -m pip install -e .

backend:
	PYTHONPATH=project python -m backend.main

frontend:
	PYTHONPATH=project python -m frontend.main

run: backend
