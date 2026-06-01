MAKEFLAGS += -rR
.SUFFIXES:
all: build/a build/b

build:
	mkdir -p $@

build/a: | build
	sleep 5; echo hi > $@

build/b: | build
	sleep 5; echo hi > $@
