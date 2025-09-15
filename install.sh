#!/bin/bash

# Plex File Renamer - Universal Installation Script
# Supports: Linux, macOS, Windows (Git Bash/WSL)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="trentmillar"
REPO_NAME="plex-file-namer"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/plex-renamer"

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi
}

# Fetch available releases from GitHub
fetch_releases() {
    echo -e "${BLUE}Fetching available releases...${NC}"
    
    # Get releases from GitHub API
    if command -v curl &> /dev/null; then
        RELEASES=$(curl -s "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases" | grep '"tag_name"' | cut -d '"' -f 4 | head -20)
    elif command -v wget &> /dev/null; then
        RELEASES=$(wget -qO- "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases" | grep '"tag_name"' | cut -d '"' -f 4 | head -20)
    else
        echo -e "${RED}Error: Neither curl nor wget found. Please install one.${NC}"
        exit 1
    fi
    
    if [ -z "$RELEASES" ]; then
        echo -e "${YELLOW}No releases found. Installing from main branch...${NC}"
        VERSION="main"
        return
    fi
    
    # Convert to array
    RELEASE_ARRAY=($RELEASES)
    LATEST="${RELEASE_ARRAY[0]}"
}

# Let user select version
select_version() {
    if [ "$VERSION" == "main" ]; then
        return
    fi
    
    echo -e "${GREEN}Available versions:${NC}"
    echo "  [0] Latest ($LATEST) - Recommended"
    
    i=1
    for release in $RELEASES; do
        echo "  [$i] $release"
        ((i++))
    done
    
    echo ""
    read -p "Select version [0-$((i-1))], or press Enter for latest: " selection
    
    if [ -z "$selection" ] || [ "$selection" == "0" ]; then
        VERSION="$LATEST"
    else
        RELEASE_ARRAY=($RELEASES)
        VERSION="${RELEASE_ARRAY[$selection]}"
    fi
    
    if [ -z "$VERSION" ]; then
        VERSION="$LATEST"
    fi
    
    echo -e "${GREEN}Installing version: $VERSION${NC}"
}

# Check and install Python
install_python() {
    echo -e "${BLUE}Checking Python installation...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
        return
    fi
    
    echo -e "${YELLOW}Python not found. Installing...${NC}"
    
    case $OS in
        linux)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y python3 python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip
            elif command -v pacman &> /dev/null; then
                sudo pacman -S python python-pip
            else
                echo -e "${RED}Could not install Python. Please install manually.${NC}"
                exit 1
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install python3
            else
                echo -e "${YELLOW}Homebrew not found. Installing Homebrew first...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew install python3
            fi
            ;;
        windows)
            echo -e "${YELLOW}Please install Python from: https://www.python.org/downloads/${NC}"
            echo "After installation, run this script again."
            exit 1
            ;;
    esac
}

# Check and install ffmpeg
install_ffmpeg() {
    echo -e "${BLUE}Checking ffmpeg installation...${NC}"
    
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
        echo -e "${GREEN}✓ ffmpeg $FFMPEG_VERSION found${NC}"
        return
    fi
    
    echo -e "${YELLOW}ffmpeg not found. Installing...${NC}"
    
    case $OS in
        linux)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y ffmpeg
            elif command -v yum &> /dev/null; then
                sudo yum install -y ffmpeg
            elif command -v pacman &> /dev/null; then
                sudo pacman -S ffmpeg
            else
                echo -e "${YELLOW}Could not install ffmpeg automatically.${NC}"
                echo "Please install ffmpeg manually: https://ffmpeg.org/download.html"
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install ffmpeg
            else
                echo -e "${YELLOW}Please install ffmpeg manually: https://ffmpeg.org/download.html${NC}"
            fi
            ;;
        windows)
            echo -e "${YELLOW}Please install ffmpeg from: https://ffmpeg.org/download.html${NC}"
            echo "Or use: choco install ffmpeg (if you have Chocolatey)"
            ;;
    esac
}

# Download and install plex-file-renamer
install_plex_renamer() {
    echo -e "${BLUE}Downloading Plex File Renamer $VERSION...${NC}"
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Download URL
    if [ "$VERSION" == "main" ]; then
        DOWNLOAD_URL="https://github.com/$REPO_OWNER/$REPO_NAME/archive/main.zip"
    else
        DOWNLOAD_URL="https://github.com/$REPO_OWNER/$REPO_NAME/releases/download/$VERSION/plex-file-renamer-$VERSION.zip"
    fi
    
    # Download
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    if command -v curl &> /dev/null; then
        curl -L "$DOWNLOAD_URL" -o release.zip
    else
        wget "$DOWNLOAD_URL" -O release.zip
    fi
    
    # Extract
    unzip -q release.zip
    cd plex-file-namer-*
    
    # Install Python dependencies
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip3 install --user -r requirements.txt
    
    # Copy main script
    cp plex_file_renamer.py "$INSTALL_DIR/plex-renamer"
    chmod +x "$INSTALL_DIR/plex-renamer"
    
    # Add shebang if not present
    if ! head -n1 "$INSTALL_DIR/plex-renamer" | grep -q "^#!"; then
        sed -i '1i#!/usr/bin/env python3' "$INSTALL_DIR/plex-renamer"
    fi
    
    # Copy other files
    [ -f "README.md" ] && cp README.md "$CONFIG_DIR/"
    
    # Create sample config if it doesn't exist
    if [ ! -f "$HOME/.plex-renamer.conf" ]; then
        cat > "$HOME/.plex-renamer.conf" << EOF
[default]
# TMDb API key (get free key from https://www.themoviedb.org/settings/api)
# api_key = your_api_key_here

# Default media type: auto, movie, or tv
default_type = auto

# Only detect years in parentheses format (2004)
parentheses_only = false

# Skip confirmation prompts for batch operations
skip_confirmation = false
EOF
        echo -e "${GREEN}✓ Created sample config at ~/.plex-renamer.conf${NC}"
    fi
    
    # Clean up
    cd /
    rm -rf "$TEMP_DIR"
}

# Add to PATH
update_path() {
    echo -e "${BLUE}Updating PATH...${NC}"
    
    # Determine shell config file
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    else
        SHELL_CONFIG="$HOME/.profile"
    fi
    
    # Check if already in PATH
    if echo "$PATH" | grep -q "$INSTALL_DIR"; then
        echo -e "${GREEN}✓ $INSTALL_DIR already in PATH${NC}"
    else
        # Add to PATH
        echo "" >> "$SHELL_CONFIG"
        echo "# Added by Plex File Renamer installer" >> "$SHELL_CONFIG"
        echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_CONFIG"
        
        echo -e "${GREEN}✓ Added $INSTALL_DIR to PATH in $SHELL_CONFIG${NC}"
        echo -e "${YELLOW}Note: Run 'source $SHELL_CONFIG' or restart your terminal${NC}"
    fi
}

# Main installation
main() {
    echo -e "${GREEN}🎬 Plex File Renamer - Installation Script${NC}"
    echo "============================================"
    echo ""
    
    # Detect OS
    detect_os
    echo -e "${BLUE}Detected OS: $OS${NC}"
    
    # Fetch releases and let user select
    fetch_releases
    select_version
    
    # Install dependencies
    install_python
    install_ffmpeg
    
    # Install plex-renamer
    install_plex_renamer
    
    # Update PATH
    update_path
    
    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo "To get started:"
    echo "  1. Get a free TMDb API key: https://www.themoviedb.org/settings/api"
    echo "  2. Edit ~/.plex-renamer.conf and add your API key"
    echo "  3. Run: plex-renamer --help"
    echo ""
    echo "If 'plex-renamer' is not found, run:"
    echo "  source $SHELL_CONFIG"
    echo "Or add this to your PATH:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
}

# Run main
main
