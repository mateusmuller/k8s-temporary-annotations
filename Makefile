.DEFAULT_GOAL := build

run: build
	@docker run -p 8443:8443 temporary_annotations:latest

build:
	@docker build -t temporary_annotations:latest .