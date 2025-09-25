# 🎬 Plex File Renamer

A powerful Python tool that automatically renames your video files to follow Plex naming conventions by fetching metadata from The Movie Database (TMDb). Say goodbye to manual renaming and hello to perfectly organized media libraries!

## ✨ Features

- 🎯 **Smart Detection**: Automatically distinguishes between movies and TV shows
- 📁 **Folder Analysis**: Extracts show names and seasons from folder structure
- 🔍 **Flexible Parsing**: Handles various filename patterns (S01E01, 1x01, E01, etc.)
- 🎬 **Episode Titles**: Fetches actual episode titles from TMDb API
- 🎨 **Quality Detection**: Automatically detects and preserves quality/source info from actual video analysis
- 🛡️ **Safety First**: Creates backup files for easy reverting
- 📺 **Plex-Perfect**: Follows official Plex naming conventions exactly
- 🌐 **Free API**: Uses TMDb's free API (no subscription required)
- 🚀 **Batch Processing**: Process entire folders recursively
- 👀 **Preview Mode**: See changes before applying them
- 🔄 **Multi-Rename Support**: Preserves original filename across multiple renames
- 🎞️ **Cinematic Aspect Ratios**: Correctly detects resolution for wide aspect ratio videos
- 📂 **Movie Folder Detection**: Won't misidentify movies as TV shows when in "Movies" folders
- ✅ **Interactive Confirmation**: Prompts before each rename (with option to skip)
- ⏱️ **Smart Duration Matching**: When multiple matches exist, uses video duration to find the correct movie/show
- 🔢 **Roman Numeral Support**: Automatically handles sequel numbering (II ↔ 2, III ↔ 3, etc.)
- 🏷️ **TMDb ID Integration**: Adds {tmdb-id} to filenames for accurate Plex matching
- 🎬 **Edition Support**: Properly tags Director's Cut, Criterion, Extended editions using {edition-name}
- ⚡ **Skip Formatted Files**: Option to skip already-processed files with TMDb IDs
- 📅 **Date-Based TV Shows**: Advanced pattern matching for date-based episodes (news shows, daily shows)
- 🔧 **Robust File Processing**: Dynamic file discovery prevents errors during batch renaming
- 🎯 **Negative Patterns**: Use {TITLE?} syntax to ignore extracted values while using explicit show names

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

# Skip files already properly formatted with TMDb IDs
python plex_file_renamer.py /path/to/videos --skip-formatted --rename
```

### Advanced Pattern Matching

For complex file structures, use custom patterns to extract show names and dates:

```bash
# Pattern for date-based TV shows (e.g., News shows, Late Night shows)
# Note: No --root-folder needed when using main path argument
python plex_file_renamer.py /path/to/videos --pattern "SHOW_NAME/DATE_FORMAT{YYYY-MM-DD}/IGNORE" --rename

# Pattern variations for different date formats and structures
python plex_file_renamer.py /path/to/videos --pattern "SHOW_NAME/DATE_FORMAT{YEAR}/{TITLE?}.{DD-MM-YY}" --rename
python plex_file_renamer.py /path/to/videos --pattern "SHOW_NAME/DATE_FORMAT{DD-MM-YYYY}/IGNORE" --rename

# Examples:
# File: /Shows/The Daily Show/2023-03-15/episode.mp4
# Pattern: "SHOW_NAME/DATE_FORMAT{YYYY-MM-DD}/IGNORE"
# Result: The Daily Show (2024) - 2023-03-15.mp4

# File: /Coronation Street/2015/01-2015/Corrie.02.01.15.PT1.mp4  
# Pattern: "SHOW_NAME/DATE_FORMAT{YEAR}/{TITLE?}.{DD-MM-YY}"
# Result: Coronation Street (1960) - s56e01 - Fri Jan 02 2015 Part 1.mp4

# Use explicit show name when folder structure doesn't contain it clearly
python plex_file_renamer.py /path/to/videos --pattern "DATE_FORMAT{YEAR}/{TITLE?}.{DD-MM-YY}" --show-name "Coronation Street" --rename
```

**Pattern placeholders:**
- `SHOW_NAME`: Extracts the show name from folder structure
- `DATE_FORMAT{format}`: Extracts dates in specified format (YYYY-MM-DD, DD-MM-YY, M-DD-YY, etc.)
- `{TITLE?}`: Negative pattern - matches title but ignores it (use with --show-name)
- `IGNORE`: Ignores parts of the path
- Pattern matching is case-insensitive

**Date-based Episode Lookup:**
When using date patterns with explicit show names, the tool automatically:
1. Searches TMDb for the show (without year filtering for long-running shows)
2. Looks up the actual episode that aired on the extracted date
3. Finds the correct season and episode numbers
4. Uses the real episode title from TMDb

This is perfect for long-running daily shows like Coronation Street, news programs, or talk shows where episodes are identified by air date rather than arbitrary season/episode numbers.

### Reverting Changes

```bash
# Preview what would be reverted
python plex_file_renamer.py /path/to/videos --revert --dry-run

# Revert all renames (with confirmation prompt)
python plex_file_renamer.py /path/to/videos --revert
```

## 🏷️ TMDb ID Support

The tool automatically adds TMDb IDs to help Plex accurately identify content:

### Format
- **Movies**: `Title (Year) {tmdb-id} [quality].ext`
- **TV Shows**: `Title (Year) {tmdb-id} - sXXeXX - Episode [quality].ext`

### Benefits
- Guarantees correct metadata matching in Plex
- Prevents misidentification of similar titles
- Works with foreign and obscure content
- Speeds up Plex library scanning

### Example
**Input:** `avatar.mkv`
**Output:** `Avatar (2009) {tmdb-19995} [1080p H264 AAC].mkv`

## 🎬 Edition Support (Plex Pass Feature)

Properly tags different movie editions using Plex's `{edition-name}` format:

### Supported Editions
- **Director's Cut** → `{edition-Director's Cut}`
- **Theatrical** → `{edition-Theatrical}`
- **Extended** → `{edition-Extended}`
- **Unrated** → `{edition-Unrated}`
- **Criterion** → `{edition-Criterion}`
- **Special Edition** → `{edition-Special Edition}`
- **Collector's Edition** → `{edition-Collector's Edition}`
- **Final Cut** → `{edition-Final Cut}`
- **Remastered** → `{edition-Remastered}`
- **Omnibus** → `{edition-Omnibus}`
- **Special** → `{edition-Special}`
- **Extra** → `{edition-Extra}`
- **Highlights** → `{edition-Highlights}`
- **Compilation** → `{edition-Compilation}`

### Examples
**Input:** `Blade Runner - Director's Cut.mp4`
**Output:** `Blade Runner (1982) {tmdb-78} {edition-Director's Cut} [1080p H264 AAC].mp4`

**Input:** `Eyimofe This Is My Desire (2020) - Criterion.mkv`
**Output:** `Eyimofe This Is My Desire (2020) {tmdb-123456} {edition-Criterion} [1080p HEVC EAC3].mkv`

**Input:** `The Beatles Anthology - Omnibus.mp4`
**Output:** `The Beatles Anthology (1995) {tmdb-12345} {edition-Omnibus} [720p H264 AAC].mp4`

**Input:** `Marvel Studios Legends - Compilation.mkv`
**Output:** `Marvel Studios Legends (2021) {tmdb-67890} {edition-Compilation} [1080p H264 EAC3].mkv`

## 🎯 Examples

### Movie Examples

**Input:** `avatar_2009.mp4`  
**Output:** `Avatar (2009) {tmdb-19995} [1080p H264 AAC].mp4`

**Input:** `The Dark Knight - 2008.mkv`  
**Output:** `The Dark Knight (2008) {tmdb-155} [1080p H264 DTS].mkv`

**Input:** `inception (2010).avi`  
**Output:** `Inception (2010) {tmdb-27205} [720p MPEG4 MP3].avi`

**Input:** `devil.in.a.blue.dress.1995.remastered.bdrip.x264-pignus.mkv`  
**Output:** `Devil in a Blue Dress (1995) {tmdb-10889} {edition-Remastered} [1080p BDRIP H264].mkv`

### TV Show Examples

**Input:** `breaking_bad_s01e01.mkv`  
**Output:** `Breaking Bad (2008) {tmdb-1396} - s01e01 - Pilot [1080p H264 AAC].mkv`

**Input:** `The Office 2x05.mp4`  
**Output:** `The Office (2005) {tmdb-2316} - s02e05 - Halloween [720p H264 AAC].mp4`

**Input:** `Friends.1.01.The.One.Where.Monica.Gets.a.Roommate.mkv`  
**Output:** `Friends (1994) {tmdb-1668} - s01e01 - The One Where Monica Gets a Roommate [1080p H264 AC3].mkv`

**Input:** `breaking_bad_s01e01_1080p_bluray_x264.mkv`  
**Output:** `Breaking Bad (2008) {tmdb-1396} - s01e01 - Pilot [1080p BLURAY H264].mkv`

**Input:** `the_office_2x05_webdl_720p.mp4`  
**Output:** `The Office (2005) {tmdb-2316} - s02e05 - Halloween [720p WEBDL H264 AAC].mp4`

### Date-Based TV Show Examples

**Input:** `Corrie.02.01.15.PT1.mp4` (with pattern `{TITLE?}.{DD-MM-YY}` and `--show-name "Coronation Street"`)  
**Output:** `Coronation Street (1960) {tmdb-291} - s56e01 - Fri Jan 02 2015 Part 1 [400p H264 AAC].mp4`

**Input:** `coronation.street.2019.02.13.part.2.web.x264-kompost[eztv].mkv`  
**Output:** `Coronation Street (1960) {tmdb-291} - s60e29 - Wed Feb 13 2019 Part 2 [480p WEB H264 AAC].mkv`

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
| `--pattern` | Custom pattern for complex file structures | `--pattern "SHOW_NAME/DATE_FORMAT{YEAR}/{TITLE?}.{DD-MM-YY}"` |
| `--show-name` | Explicitly specify show name when not in folder structure | `--show-name "Coronation Street"` |
| `--skip-formatted` | Skip files already formatted with TMDb IDs | `--skip-formatted` |

## 🎬 Sample Output

```
Processing: /Users/john/Videos/breaking_bad_s01e01_1080p_bluray.mkv
--------------------------------------------------
Video duration: 47.2 minutes
Resolution: 1080p
Video codec: H264
Audio codec: AAC
Parsed title: breaking bad
Parsed episode: S01E01
TV show detected: True
⚠️ WARNING: --type movie specified but detected TV show with S01E01
   Overriding to --type tv for proper TV show processing
Detected type: tv

Searching TMDb for: breaking bad
Found TV show: Breaking Bad (2008)
Found episode title: Pilot
Optional info: 1080p BLURAY H264 AAC

[DRY RUN] Would rename:
  From: breaking_bad_s01e01_1080p_bluray.mkv
  To:   Breaking Bad (2008) {tmdb-1396} - s01e01 - Pilot [1080p BLURAY H264 AAC].mkv
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

### Smart Duration Matching

When multiple movies/shows have similar names, the script uses video duration to find the correct match:

1. **Exact Name Priority**: If the search finds an exact name match with duration within ±2 minutes, it's selected
2. **Best Duration Match**: Otherwise, finds the match with duration closest to but higher than the file's duration
3. **Fallback**: If no higher duration exists, uses the closest match overall

Example: When searching for "Bloodsport", if both "Bloodsport (1988)" and "Bloodsport III (1996)" are found, it will choose "Bloodsport (1988)" as the exact name match, even if "Bloodsport III" has a closer duration.

### Roman Numeral Support

The script automatically handles different sequel numbering formats:

- **Automatic conversion**: "Rocky 2" ↔ "Rocky II"
- **Smart searching**: Searches for both number and Roman numeral versions
- **Exact matching**: "Cannonball Run 2" correctly matches "Cannonball Run II" in TMDb

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

The script detects quality information from **actual video analysis** using ffmpeg, not just filename claims:

**Detected from file:**
- **Resolution:** Actual video resolution (1080p, 720p, 4K, etc.) from video stream
- **Video Codec:** Real codec used (H264, H265/HEVC, MPEG4, VP9, etc.)
- **Audio Codec:** Actual audio format (AAC, DTS, AC3, MP3, etc.)

**Preserved from filename:**
- **Sources:** `BluRay`, `WEB-DL`, `HDTV`, `WEBRip` (can't be detected from file)
- **Special:** `PROPER`, `REPACK`, `EXTENDED`, `UNRATED`, `REMASTERED`

**Smart handling:**
- If filename claims "1080p" but file is actually 720p, uses real resolution
- Combines actual file properties with source info from filename
- Quality info is preserved in `[brackets]` which Plex ignores for matching but keeps for user reference

Example: `movie.1080p.BluRay.x264.mkv` analyzed as 720p H265 becomes:
`Movie Title (2024) [720p BLURAY H265].mkv`

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

## ⚡ Skip Already-Formatted Files

The `--skip-formatted` flag intelligently skips files that are already properly formatted:

### Detection Criteria
Files are skipped if they have:
1. Year in parentheses: `(2020)`
2. TMDb ID: `{tmdb-123}`
3. Backup file: `filename.original.txt`

### Use Cases
- **Large Collections**: Re-process directories without touching completed files
- **Incremental Updates**: Add new files to an existing organized library
- **Batch Processing**: Safely re-run on partially completed jobs
- **Performance**: No API calls for already-identified content

### Example
```bash
# First run - processes all files
python plex_file_renamer.py /movies --rename

# Later runs - only processes new/unformatted files
python plex_file_renamer.py /movies --rename --skip-formatted
```

Output:
```
[1/3] Processing: Avatar (2009) {tmdb-19995} [1080p H264 AAC].mkv
✓ File already properly formatted with TMDb ID and has backup file, skipping

[2/3] Processing: new_movie_2024.mkv
Video duration: 120.5 minutes
Searching TMDb for: new movie 2024
...
```

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

**Pattern Matching Issues**
```
❌ Pattern did not match - falling back to standard parsing
```
- Check that your pattern matches your folder structure
- For `/Show/2015/01-2015/file.ext`, use pattern `SHOW_NAME/DATE_FORMAT{YEAR}/IGNORE/filename`
- Use `{TITLE?}` for parts you want to ignore but need to match

**"File not found" Errors During Batch Processing**
- Fixed in recent versions with dynamic file discovery
- Files renamed during processing no longer cause errors for remaining files
- If you see this on older versions, update to the latest release

**Date Extraction Issues**
```
Extracted air date from filename: 2013-02-19  # Wrong date
```
- Recent versions prioritize YYYY-MM-DD format over DD-MM-YY
- For `file.2019.02.13.ext`, now correctly extracts `2019-02-13`
- Use explicit patterns for ambiguous dates

**TMDb Search Failures for Long-Running Shows**
```
TV show not found in TMDb
```
- For shows like "Coronation Street" with explicit `--show-name`, year filtering is now disabled
- Searches for show without episode year to find long-running series that started decades ago

### Debug Information

The script provides detailed debug output:
- Parsed title and year information
- Season detection from folders vs filenames
- TV show vs movie detection reasoning
- TMDb search results and matches
- Pattern matching steps and failures
- Date extraction and conversion process

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


## 🔧 Recent Technical Improvements

### Version 2.1.0+ Features

1. **🔧 Robust Batch Processing**
   - Dynamic file discovery prevents "file not found" errors during batch operations
   - Files that get renamed no longer break processing of remaining files
   - Iteration safety with maximum loop protection
   - Graceful handling of missing files during large batch operations

2. **📅 Enhanced Date-Based Episode Lookup**
   - Improved date pattern recognition prioritizing YYYY-MM-DD format
   - Automatic episode lookup by air date for long-running shows
   - Searches through all seasons to find episodes by broadcast date
   - No more fake season/episode numbers for date-based shows

3. **🎯 Advanced Pattern Matching**
   - Negative patterns with `{TITLE?}` syntax for ignoring extracted values
   - Better handling of dot-separated filenames
   - Flexible pattern matching that works without explicit root folders
   - Smart fallback when pattern matching fails

4. **🔍 Improved TMDb Search Logic**
   - Long-running shows no longer filtered by episode year
   - Better handling of shows that started decades before current episodes
   - Exact name matching takes precedence over duration proximity
   - Roman numeral conversion for sequel matching

5. **🛡️ Error Prevention & Recovery**
   - Early variable initialization prevents "referenced before assignment" errors
   - Comprehensive existence checks before file operations
   - Better error messages and debugging information
   - Graceful degradation when pattern matching fails

## 🎯 Future Enhancements

### Usability Improvements We're Considering

1. **🔗 Plex Integration**
   - Direct Plex library scanning
   - Automatic metadata refresh
   - Library health checking

2. **🎨 Enhanced Detection**
   - Better pattern matching for edge cases
   - Support for more languages
   - Custom naming templates

3. **📊 Analytics & Reporting**
   - Processing statistics
   - File organization insights
   - Library health reports

4. **🔌 Plugin System**
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
