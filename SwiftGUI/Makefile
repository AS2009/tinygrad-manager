# Build TinyGrad Manager (Swift GUI + Python Backend)
# Requires: Xcode 15+, Swift 5.9+, macOS 14.0+

SWIFT_BUILD := swift build -c release --arch arm64
APP_NAME := TinyGradManager
APP_DIR := $(APP_NAME).app
CONTENTS := $(APP_DIR)/Contents
MACOS_DIR := $(CONTENTS)/MacOS
RESOURCES := $(CONTENTS)/Resources

.PHONY: all swift python app clean run help

all: app

# ── Swift GUI ──────────────────────────────────────────────────────────────
swift:
	$(SWIFT_BUILD)

# ── Full .app bundle ──────────────────────────────────────────────────────
app: swift
	@echo "Creating $(APP_DIR)..."
	rm -rf $(APP_DIR)
	mkdir -p $(MACOS_DIR) $(RESOURCES)
	# Swift binary
	cp .build/release/TinyGradManager $(MACOS_DIR)/
	# Python backend
	cp -R ../TinyGradManager $(RESOURCES)/
	# Info.plist
	sed 's/$$VERSION/2.0.0/' Info.plist > $(CONTENTS)/Info.plist
	# Launch script
	echo '#!/bin/bash\nDIR="$$(cd "$$(dirname "$$0")" && pwd)"\n"$$DIR/../Resources/TinyGradManager/backend_main.py" & \n"$$DIR/TinyGradManager" &\nwait' > $(MACOS_DIR)/launch.sh
	chmod +x $(MACOS_DIR)/launch.sh
	@echo "✅ $(APP_DIR) created"

# ── Run locally (dev) ─────────────────────────────────────────────────────
run-backend:
	cd ../TinyGradManager && python3 backend_main.py

run-swift: swift
	.build/release/TinyGradManager

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	rm -rf $(APP_DIR) .build

help:
	@echo "Targets:"
	@echo "  make swift         Build Swift GUI (release, arm64)"
	@echo "  make app           Build complete .app bundle"
	@echo "  make run-backend   Run Python backend (dev)"
	@echo "  make run-swift     Run Swift GUI (dev)"
	@echo "  make clean"
