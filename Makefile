.PHONY: tests

install:
	@echo soon

clean:
	@find . -name \*.pyc -delete

reset:
	@python2 reset-database.py

tests:
	@python3 tests/*.py

stat:
	@python3 get-database-stat.py

fingerprint-songs: clean
	@python3 make-fingerprints.py

recognize-listen: clean
	@python3 recognize-from-mic.py -s $(seconds)

recognize-file: clean
	@python3 recognize-from-file.py