# 🎬 Plex File Renamer

A powerful Python tool that automatically renames your video files to follow Plex naming conventions by fetching metadata from The Movie Database (TMDb). Say goodbye to manual renaming and hello to perfectly organized media libraries!

## ✨ Features

- 🎯 **Smart Detection**: Automatically distinguishes between movies and TV shows
- 📁 **Folder Analysis**: Extracts show names and seasons from folder structure
- 🔍 **Flexible Parsing**: Handles various filename patterns (S01E01, 1x01, E01, etc.)
- 🎬 **Episode Titles**: Fetches actual episode titles from TMDb API
- 🎨 **Quality Detection**: Automatically detects and preserves quality/source info
- 🛡️ **Safety First**: Creates backup files for easy reverting
- 📺 **Plex-Perfect**: Follows official Plex naming conventions exactly
- 🌐 **Free API**: Uses TMDb's free API (no subscription required)
- 🚀 **Batch Processing**: Process entire folders recursively
- 👀 **Preview Mode**: See changes before applying them
- 🔄 **Multi-Rename Support**: Preserves original filename across multiple renames
- 🎞️ **Cinematic Aspect Ratios**: Correctly detects resolution for wide aspect ratio videos
- 📂 **Movie Folder Detection**: Won't misidentify movies as TV shows when in "Movies" folders
- ✅ **Interactive Confirmation**: Prompts before each rename (with option to skip)

## 🚀 Quick Start

### Option A: One-Line Installer (Beta - In Progress)

> ⚠️ **Note**: The automated installer is currently in beta and may have issues. For a reliable installation, use Option B (Manual Installation) below.

#### Linux/macOS
```bash
curl -sSL https://raw.githubusercontent.com/trentmillar/plex-file-namer/main/install.sh | bash
```

#### Windows PowerShell
```powershell
irm https://raw.githubusercontent.com/trentmillar/plex-file-namer/main/install.ps1 | iex
```

The installer will:
- Detect your operating system
- Show all available versions and let you choose
- Install Python and ffmpeg if needed
- Set up everything automatically
- Create a sample configuration file

### Option B: Manual Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/trentmillar/plex-file-namer.git
cd plex-file-namer

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (optional - for video duration detection)
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
# Windows
choco install ffmpeg
```

### Get TMDb API Key

1. Visit [themoviedb.org](https://www.themoviedb.org/settings/api)
2. Create a free account
3. Request an API key
4. Set your API key using one of these methods:

#### Option A: Configuration File (Recommended)
Create `~/.plex-renamer.conf`:
```ini
[default]
api_key = your_tmdb_api_key_here
default_type = auto
parentheses_only = false
skip_confirmation = false
```

#### Option B: Environment Variable
```bash
# Linux/macOS
export TMDB_API_KEY="your_api_key_here"

# Windows (Command Prompt)
set TMDB_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:TMDB_API_KEY="your_api_key_here"

# Windows (Permanent - run as Administrator)
setx TMDB_API_KEY "your_api_key_here"
```

#### Option C: Command Line
```bash
python plex_file_renamer.py /path/to/videos --api-key your_key_here
```

### Test Run

```bash
# Preview what would be renamed (safe mode)
python plex_file_renamer.py /path/to/your/videos --dry-run
```

## 📖 Usage Guide

### Basic Commands

```bash
# Preview changes (recommended first step)
python plex_file_renamer.py /path/to/videos --dry-run

# Actually rename files (with confirmation prompt for each file)
python plex_file_renamer.py /path/to/videos --rename

# Rename files without confirmation prompts (auto-approve all)
python plex_file_renamer.py /path/to/videos --rename --yes

# Process single file
python plex_file_renamer.py /path/to/video.mkv --rename

# Force movie detection
python plex_file_renamer.py /path/to/videos --type movie --rename

# Force TV show detection
python plex_file_renamer.py /path/to/videos --type tv --rename

# Only detect years in parentheses (2004), not - 2004 or space 2004
python plex_file_renamer.py /path/to/videos --parentheses-only --rename
```

### Reverting Changes

```bash
# Preview what would be reverted
python plex_file_renamer.py /path/to/videos --revert --dry-run

# Revert all renames (with confirmation prompt)
python plex_file_renamer.py /path/to/videos --revert
```

## 🎯 Examples

### Movie Examples

**Input:** `avatar_2009.mp4`  
**Output:** `Avatar (2009).mp4`

**Input:** `The Dark Knight - 2008.mkv`  
**Output:** `The Dark Knight (2008).mkv`

**Input:** `inception (2010).avi`  
**Output:** `Inception (2010).avi`

### TV Show Examples

**Input:** `breaking_bad_s01e01.mkv`  
**Output:** `Breaking Bad (2008) - s01e01 - Pilot.mkv`

**Input:** `The Office 2x05.mp4`  
**Output:** `The Office (2005) - s02e05 - Halloween.mp4`

**Input:** `Friends.1.01.The.One.Where.Monica.Gets.a.Roommate.mkv`  
**Output:** `Friends (1994) - s01e01 - The One Where Monica Gets a Roommate.mkv`

**Input:** `breaking_bad_s01e01_1080p_bluray_x264.mkv`  
**Output:** `Breaking Bad (2008) - s01e01 - Pilot [1080p BLURAY X264].mkv`

**Input:** `the_office_2x05_webdl_720p.mp4`  
**Output:** `The Office (2005) - s02e05 - Halloween [WEBDL 720P].mp4`

### Folder Structure Examples

```
# Smart folder detection
/TV Shows/Breaking Bad/S01/pilot.mkv
→ Breaking Bad (2008) - s01e01 - Pilot.mkv

/Movies/avatar_2009.mp4  
→ Avatar (2009).mp4

# Season folder detection
/Shows/The Office/Season 2/E05 Halloween.avi
→ The Office (2005) - s02e05 - Halloween.avi
```

## 🎛️ Command-Line Options

| Flag | Description | Example |
|------|-------------|---------|
| `path` | File or directory to process | `/path/to/videos` |
| `--dry-run` | Preview changes without renaming | `--dry-run` |
| `--rename` | Actually perform the renaming | `--rename` |
| `--yes`, `-y` | Skip confirmation prompt for each rename (auto-approve all) | `--yes` |
| `--type` | Force media type detection | `--type movie` |
| `--api-key` | TMDb API key (or use env var) | `--api-key abc123` |
| `--parentheses-only` | Only detect years in (2004) format | `--parentheses-only` |
| `--revert` | Revert all renames using backup files | `--revert` |

## 🎬 Sample Output

```
Processing: /Users/john/Videos/breaking_bad_s01e01_1080p_bluray.mkv
--------------------------------------------------
Video duration: 47.2 minutes
Parsed title: breaking bad
Parsed episode: S01E01
TV show detected: True
⚠️ WARNING: --type movie specified but detected TV show with S01E01
   Overriding to --type tv for proper TV show processing
Detected type: tv

Searching TMDb for: breaking bad
Found TV show: Breaking Bad (2008)
Found episode title: Pilot
Detected quality/source info: 1080P BLURAY

[DRY RUN] Would rename:
  From: breaking_bad_s01e01_1080p_bluray.mkv
  To:   Breaking Bad (2008) - s01e01 - Pilot [1080P BLURAY].mkv
```

## 🧠 Smart Detection Features

### TV Show Detection

The script automatically detects TV shows when it finds:
- **Season/Episode patterns**: `S01E01`, `1x01`, `E05`, `101`
- **Season folders**: `/S01/`, `/Season 1/`, `/2/`
- **Episode numbers**: Any episode identifier in filename

### Year Detection Priority

1. **Trailing years**: `Movie Title - 2004`, `Movie Title 2004`, `Movie Title (2004)`
2. **Parentheses format**: `Movie Title (2004)` (when using `--parentheses-only`)

### Filename Patterns Supported

**Movies:**
- `Movie Title (2004).mkv`
- `Movie Title - 2004.mp4`
- `Movie Title 2004.avi`

**TV Shows:**
- `Show S01E01.mkv` → Season 1, Episode 1
- `Show 1x01.mp4` → Season 1, Episode 1
- `Show E05.avi` → Episode 5 (season from folder or default to 1)
- `Show 101.mkv` → Season 1, Episode 1 (3-digit format)
- `Show 1.05.mkv` → Season 1, Episode 5

### Quality & Source Detection

The script automatically detects and preserves quality/source information:

**Quality:** `1080p`, `720p`, `480p`, `4K`, `2160p`  
**Sources:** `BluRay`, `WEB-DL`, `HDTV`, `WEBRip`  
**Codecs:** `x264`, `x265`, `HEVC`, `H264`  
**Audio:** `AAC`, `DTS`, `AC3`, `MP3`  
**Special:** `PROPER`, `REPACK`, `EXTENDED`, `UNRATED`

Quality info is preserved in `[brackets]` which Plex ignores for matching but keeps for user reference.

## 🛡️ Safety Features

### Backup System

When files are renamed, backup files are automatically created:

**Backup file:** `New Filename.original.txt`
```
Original filename: old_name.mkv
Original full path: /full/path/to/old_name.mkv
Renamed to: New Filename.mkv
Renamed on: 2025-01-15T10:30:45.123456

# To revert: mv 'New Filename.mkv' 'old_name.mkv'
```

### Safety Checks

- ✅ **Preview mode**: Always test with `--dry-run` first
- ✅ **Conflict detection**: Won't overwrite existing files
- ✅ **Backup creation**: Automatic backup files for reverting
- ✅ **Confirmation prompts**: Asks before reverting changes
- ✅ **Error handling**: Graceful handling of API failures

## 📁 Supported File Types

**Video formats:**
`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.3gp`, `.3g2`, `.ts`, `.mts`, `.m2ts`, `.vob`, `.ogv`, `.divx`, `.xvid`, `.rm`, `.rmvb`

## 🔧 Troubleshooting

### Common Issues

**"No TMDb API key found"**
```bash
export TMDB_API_KEY="your_api_key_here"
# Or pass directly: --api-key your_api_key_here
```

**"Error getting video duration: No such file or directory: 'ffprobe'"**
- FFmpeg is not installed (optional feature)
- Install with: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Ubuntu)

**macOS Permission Issues**
1. Open **System Settings** → **Privacy & Security** → **Files and Folders**
2. Grant Terminal/VS Code access to **Network Volumes**
3. Or add to **Full Disk Access**

**TV Show in Season Folder but Detected as Movie**
```
⚠️ WARNING: File is in season folder 'S01' but has no episode number!
   Consider renaming to include episode number (e.g., S01E01, E01, etc.)
```

### Debug Information

The script provides detailed debug output:
- Parsed title and year information
- Season detection from folders vs filenames
- TV show vs movie detection reasoning
- TMDb search results and matches

## 🚀 Advanced Usage

### Configuration File

The script supports a configuration file at `~/.plex-renamer.conf` for persistent settings:

```ini
[default]
# TMDb API key (no need to set environment variable)
api_key = your_tmdb_api_key_here

# Default media type: auto, movie, or tv
default_type = auto

# Only detect years in parentheses format (2004)
parentheses_only = false

# Skip confirmation prompts for batch operations
skip_confirmation = false
```

**Priority order for settings:**
1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration file (lowest priority)

### Batch Processing Tips

```bash
# Process multiple folders
for dir in /media/TV/* ; do
    python plex_file_renamer.py "$dir" --type tv --rename
done

# Process by file type
find /media -name "*.mkv" -exec python plex_file_renamer.py {} --rename \;
```


## 🎯 Future Enhancements

### Usability Improvements We're Considering

1. **📦 One-Click Installation**
   ```bash
   curl -sSL install.plex-renamer.com | bash
   ```

2. **🔗 Plex Integration**
   - Direct Plex library scanning
   - Automatic metadata refresh
   - Library health checking

3. **🎨 Enhanced Detection**
   - Better pattern matching for edge cases
   - Support for more languages
   - Custom naming templates

4. **📊 Analytics & Reporting**
   - Processing statistics
   - File organization insights
   - Library health reports

5. **🔌 Plugin System**
   - Custom naming rules
   - Additional metadata sources
   - Integration with other tools

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 💡 Tips for Best Results

1. **Always start with `--dry-run`** to preview changes
2. **Use specific folder structures** for TV shows when possible
3. **Include years in filenames** for better movie detection
4. **Organize by media type** (separate Movies and TV Shows folders)
5. **Keep original files** until you're satisfied with the results
6. **Use the revert feature** if something goes wrong

## ⭐ Star History

If this tool helps organize your media library, please consider giving it a star! ⭐

---

**Happy organizing! 🎬📺**
