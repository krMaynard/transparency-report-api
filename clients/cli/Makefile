.PHONY: build test lint install clean

build:
	go build -o bin/dsa-research-pp-cli ./cmd/dsa-research-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/dsa-research-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/dsa-research-pp-mcp ./cmd/dsa-research-pp-mcp

install-mcp:
	go install ./cmd/dsa-research-pp-mcp

build-all: build build-mcp
