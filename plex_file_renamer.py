#!/usr/bin/env python3
"""
Plex File Renamer - Inspect video files, fetch metadata, and rename according to Plex conventions
"""

import os
import re
import sys
import configparser
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Video inspection - using ffmpeg-python for better compatibility
try:
    import ffmpeg
except ImportError:
    print("Please install ffmpeg-python: pip install ffmpeg-python")
    sys.exit(1)

# HTTP requests for API calls
try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


class VideoInspector:
    """Inspect video files to get metadata like duration"""
    
    @staticmethod
    def get_video_duration(file_path: str) -> float:
        """Get video duration in seconds using ffmpeg"""
        try:
            probe = ffmpeg.probe(file_path)
            # Try format duration first (most reliable)
            if 'format' in probe and 'duration' in probe['format']:
                return float(probe['format']['duration'])
            
            # Fallback to stream duration
            for stream in probe.get('streams', []):
                if 'duration' in stream:
                    return float(stream['duration'])
            
            print("No duration information found in video file")
            return 0.0
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return 0.0
    
    @staticmethod
    def get_media_info(file_path: str) -> Dict[str, Any]:
        """
        Get detailed media information from video file using ffmpeg probe
        Returns dict with resolution, video codec, audio codec, etc.
        """
        media_info = {
            'resolution': None,
            'video_codec': None,
            'audio_codec': None,
            'duration': 0.0
        }
        
        try:
            probe = ffmpeg.probe(file_path)
            
            # Get duration
            if 'format' in probe and 'duration' in probe['format']:
                media_info['duration'] = float(probe['format']['duration'])
            
            # Parse streams for video and audio info
            for stream in probe.get('streams', []):
                if stream['codec_type'] == 'video' and not media_info['video_codec']:
                    # Get video codec
                    codec_name = stream.get('codec_name', '').lower()
                    if codec_name:
                        # Map common codec names to display format
                        codec_map = {
                            'h264': 'H264',
                            'avc': 'H264',
                            'h265': 'H265',
                            'hevc': 'HEVC',
                            'mpeg4': 'MPEG4',
                            'vp9': 'VP9',
                            'vp8': 'VP8',
                            'av1': 'AV1'
                        }
                        media_info['video_codec'] = codec_map.get(codec_name, codec_name.upper())
                    
                    # Get resolution
                    width = stream.get('width')
                    height = stream.get('height')
                    if width and height:
                        # Store raw resolution for debugging
                        media_info['raw_resolution'] = f"{width}x{height}"
                        
                        # Determine quality based on resolution
                        # Use width OR height to handle different aspect ratios
                        # Many movies use cinematic aspect ratios (e.g., 1920x800)
                        if height >= 2160 or width >= 3840:
                            media_info['resolution'] = '4K'
                        elif height >= 1440 or width >= 2560:
                            media_info['resolution'] = '1440p'
                        elif height >= 1080 or width >= 1920:
                            media_info['resolution'] = '1080p'
                        elif height >= 720 or width >= 1280:
                            media_info['resolution'] = '720p'
                        elif height >= 480 or width >= 854:
                            media_info['resolution'] = '480p'
                        else:
                            media_info['resolution'] = f'{height}p'
                
                elif stream['codec_type'] == 'audio' and not media_info['audio_codec']:
                    # Get audio codec
                    codec_name = stream.get('codec_name', '').lower()
                    if codec_name:
                        # Map common audio codec names
                        audio_map = {
                            'aac': 'AAC',
                            'ac3': 'AC3',
                            'eac3': 'EAC3',
                            'dts': 'DTS',
                            'mp3': 'MP3',
                            'vorbis': 'OGG',
                            'opus': 'OPUS',
                            'flac': 'FLAC',
                            'truehd': 'TrueHD',
                            'dca': 'DTS'
                        }
                        media_info['audio_codec'] = audio_map.get(codec_name, codec_name.upper())
        
        except Exception as e:
            print(f"Note: Could not get detailed media info: {e}")
        
        return media_info


class TMDbAPI:
    """Interface to The Movie Database (TMDb) API - free and open source"""
    
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key (get free key from themoviedb.org)"""
        # Priority: 1. Passed parameter, 2. Environment variable, 3. Config file
        self.api_key = api_key or os.environ.get('TMDB_API_KEY')
        
        # Try loading from config file if not found yet
        if not self.api_key:
            config = load_config()
            self.api_key = config.get('api_key')
        
        if not self.api_key:
            print("\nNo TMDb API key found!")
            print("Please either:")
            print("1. Set TMDB_API_KEY environment variable")
            print("2. Pass --api-key parameter")
            print("3. Create ~/.plex-renamer.conf with api_key setting")
            print("\nGet a free API key at: https://www.themoviedb.org/settings/api")
            sys.exit(1)
    
    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a movie by title and optional year"""
        params = {
            'api_key': self.api_key,
            'query': title
        }
        if year:
            params['year'] = year
        
        try:
            response = requests.get(f"{self.BASE_URL}/search/movie", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                # Return the first (most relevant) result
                return data['results'][0]
        except requests.exceptions.RequestException as e:
            print(f"Error searching for movie: {e}")
        
        return None
    
    def search_tv(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a TV show by title and optional year"""
        params = {
            'api_key': self.api_key,
            'query': title
        }
        if year:
            params['first_air_date_year'] = year
        
        try:
            response = requests.get(f"{self.BASE_URL}/search/tv", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                return data['results'][0]
        except requests.exceptions.RequestException as e:
            print(f"Error searching for TV show: {e}")
        
        return None
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed movie information"""
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(f"{self.BASE_URL}/movie/{movie_id}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting movie details: {e}")
        
        return None
    
    def get_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed TV show information"""
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(f"{self.BASE_URL}/tv/{tv_id}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting TV show details: {e}")
        
        return None
    
    def get_episode_details(self, tv_id: int, season_number: int, episode_number: int) -> Optional[Dict[str, Any]]:
        """Get detailed episode information including title"""
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/tv/{tv_id}/season/{season_number}/episode/{episode_number}", 
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting episode details: {e}")
        
        return None


class PlexFileNamer:
    """Format filenames according to Plex naming conventions"""
    
    @staticmethod
    def detect_season_from_folder(file_path: Path) -> Optional[int]:
        """
        Detect season number from folder structure
        Looks for patterns like: S01, S1, Season 1, Season01, etc.
        """
        parent_folder = file_path.parent.name
        
        season_patterns = [
            r'^[Ss](\d+)$',                    # S1, S01, s1, s01
            r'^[Ss]eason\s*(\d+)$',           # Season 1, Season01, season 1
            r'^(\d+)$',                        # Just a number (1, 01)
        ]
        
        for pattern in season_patterns:
            match = re.match(pattern, parent_folder, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    @staticmethod
    def extract_show_name_from_path(file_path: Path) -> Optional[str]:
        """
        Extract TV show name from folder structure
        If parent folder is season folder, use grandparent as show name
        """
        parent_folder = file_path.parent.name
        
        # Check if parent folder is a season folder
        season_patterns = [
            r'^[Ss]\d+$',                     # S1, S01
            r'^[Ss]eason\s*\d+$',            # Season 1, Season01
            r'^\d+$',                         # Just a number
        ]
        
        is_season_folder = any(re.match(pattern, parent_folder, re.IGNORECASE) for pattern in season_patterns)
        
        if is_season_folder and file_path.parent.parent.name:
            # Use grandparent folder as show name
            show_name = file_path.parent.parent.name
        else:
            # Use parent folder as show name
            show_name = parent_folder
        
        # Clean up the show name
        show_name = re.sub(r'[._-]+', ' ', show_name).strip()
        return show_name if show_name else None
    
    @staticmethod
    def parse_filename(filename: str, parentheses_only: bool = False, skip_episode_detection: bool = False) -> Tuple[str, Optional[int], Optional[str], Optional[str]]:
        """
        Parse filename to extract title, year, season, and episode
        
        Args:
            filename: The filename to parse
            parentheses_only: If True, only look for years in parentheses (2004)
            skip_episode_detection: If True, skip episode/season detection (for movies)
        
        Returns: (title, year, season, episode)
        """
        # Remove file extension
        name = Path(filename).stem
        
        # Pre-process: Remove bracketed optional info (quality, codecs, etc.)
        # This handles already-renamed files like "Movie (2019) [1080p H264].mp4"
        name = re.sub(r'\s*\[.*?\]\s*', '', name)  # Remove [anything] brackets
        
        # Pre-process: Remove common release group tags and quality info at the end
        # This helps with files like "The.Matrix.1999.1080p.BluRay.x264-GROUP"
        # Only remove if it's clearly a release group (uppercase, common patterns)
        name = re.sub(r'-[A-Z][A-Z0-9]+$', '', name)  # Remove -GROUP (uppercase release groups)
        
        year = None
        
        if parentheses_only:
            # Only look for years in parentheses: " (2004)" at the end
            trailing_year_patterns = [
                r'\s*\((\d{4})\)\s*$',      # " (2004)" at end
            ]
        else:
            # Look for all year patterns including dot-separated
            trailing_year_patterns = [
                r'\.(\d{4})(?:\.|$)',       # .1999. or .1999 at end (dot-separated)
                r'\s*-\s*(\d{4})\s*$',      # " - 2004" at end
                r'\s+(\d{4})\s*$',          # " 2004" at end  
                r'\s*\((\d{4})\)\s*$',      # " (2004)" at end
            ]
        
        for pattern in trailing_year_patterns:
            match = re.search(pattern, name)
            if match:
                year = int(match.group(1))
                # Remove the year and everything after it for dot-separated files
                if '.' in name and pattern == r'\.(\d{4})(?:\.|$)':
                    name = name[:match.start()]
                else:
                    name = name[:match.start()].strip()
                break
        
        season = None
        episode = None
        
        # Skip episode detection if we're processing a movie
        if not skip_episode_detection:
            # Check for TV show patterns - PRIORITY ORDER (most specific first)
            season_episode_patterns = [
                # Patterns with both season and episode (highest priority)
                (r'[Ss](\d+)[Ee](\d+)', 'both'),                        # S01E01, S1E1
                (r'(\d+)[xX](\d+)', 'both'),                            # 1x01, 01x01  
                (r'[Ss]eason\s*(\d+)\s*[Ee]pisode\s*(\d+)', 'both'),   # Season 1 Episode 1
                (r'(\d+)\.(\d+)', 'both'),                              # 1.01, 01.01
                
                # Episode-only patterns (season from folder or default to 1)
                (r'[Ee](\d+)', 'episode'),                              # E01, E1
                (r'[Ee]pisode\s*(\d+)', 'episode'),                     # Episode 1, Episode 01
                # Only match 3-digit episode codes that are NOT at the start of the title
                # This prevents "12 Strong" from being detected as episode 12
                (r'(?<!^)(\d{3})(?!\d)', 'episode'),                    # 101, 201 (3-digit episode codes, not at start)
            ]
            
            for pattern, pattern_type in season_episode_patterns:
                match = re.search(pattern, name)
                if match:
                    if pattern_type == 'both':
                        season = match.group(1).zfill(2) 
                        episode = match.group(2).zfill(2)
                    elif pattern_type == 'episode':
                        episode_num = match.group(1)
                        
                        # Handle 3-digit episode codes (like 101 = S01E01)
                        if len(episode_num) == 3 and episode_num.startswith(('1', '2', '3', '4', '5')):
                            season = episode_num[0].zfill(2)
                            episode = episode_num[1:].zfill(2)
                        else:
                            episode = episode_num.zfill(2)
                            # Season will be determined from folder or default to 1
                    
                    # Remove the season/episode info from title
                    name = name[:match.start()].strip()
                    break
        
        # Clean up the title
        # Replace dots, underscores, and dashes with spaces
        title = re.sub(r'[._-]+', ' ', name).strip()
        # Remove any quality/source/codec info that might still be in the title
        quality_patterns = [
            r'\b\d{3,4}p\b',  # 720p, 1080p, etc.
            r'\b(?:BluRay|BLURAY|BRRip|BDRip|WEB-DL|WEBRip|HDTV|DVDRip)\b',
            r'\b(?:x264|x265|h264|h265|HEVC|XviD|DivX)\b',
            r'\b(?:AAC|AC3|DTS|MP3|FLAC)\b',
            r'\b(?:PROPER|REPACK|EXTENDED|UNRATED)\b'
        ]
        for pattern in quality_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        # Clean up multiple spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title, year, season, episode
    
    @staticmethod
    def analyze_tv_show(file_path: Path, parentheses_only: bool = False) -> Dict[str, Any]:
        """
        Comprehensive TV show analysis combining folder structure and filename
        
        Returns:
            Dict with: show_name, season, episode, year, is_tv_show
        """
        filename = file_path.name
        
        # Check if file is in a movie folder first (before parsing)
        movie_folder_names = {
            'movies', 'movie', 'films', 'film', 'cinema', 'motion pictures',
            'feature films', 'features', 'theatrical releases'
        }
        
        parent_lower = file_path.parent.name.lower()
        grandparent_lower = file_path.parent.parent.name.lower() if file_path.parent.parent.name else ''
        
        in_movie_folder = (parent_lower in movie_folder_names or 
                          grandparent_lower in movie_folder_names or
                          'movie' in parent_lower or 
                          'film' in parent_lower)
        
        # Parse filename - skip episode detection if in movie folder
        title_from_file, year, season_from_file, episode_from_file = PlexFileNamer.parse_filename(filename, parentheses_only, skip_episode_detection=in_movie_folder)
        
        # Detect season from folder structure
        season_from_folder = PlexFileNamer.detect_season_from_folder(file_path)
        
        # Extract show name from path
        show_name_from_path = PlexFileNamer.extract_show_name_from_path(file_path)
        
        # Episode detection (REQUIRED for TV shows)
        final_episode = int(episode_from_file) if episode_from_file else None
        
        # Season detection - FILENAME TAKES PRIORITY
        final_season = None
        if season_from_file:
            # Filename has season - use it
            final_season = int(season_from_file)
        elif final_episode and season_from_folder:
            # Filename has episode, folder has season - use folder season
            final_season = season_from_folder
        elif final_episode:
            # Episode in filename but no season anywhere - assume season 1
            final_season = 1
        
        # TV show determination - MUST have episode number AND not be in movie folder
        is_tv_show = bool(final_episode is not None and not in_movie_folder)
        
        # Warning for potential TV shows missing episode numbers
        has_season_folder = season_from_folder is not None
        missing_episode_warning = (has_season_folder and final_episode is None)
        
        # Show name priority:
        # 1. If filename has show name + season/episode, use filename
        # 2. If folder structure suggests show name, use that
        # 3. Use filename as fallback
        if is_tv_show and show_name_from_path and not (season_from_file and title_from_file):
            final_show_name = show_name_from_path
        else:
            final_show_name = title_from_file
        
        return {
            'show_name': final_show_name,
            'season': final_season,
            'episode': final_episode,
            'year': year,
            'is_tv_show': is_tv_show,
            'missing_episode_warning': missing_episode_warning,
            'debug_info': {
                'title_from_file': title_from_file,
                'season_from_file': season_from_file,
                'season_from_folder': season_from_folder,
                'show_name_from_path': show_name_from_path,
                'parent_folder': file_path.parent.name,
                'grandparent_folder': file_path.parent.parent.name if file_path.parent.parent.name else None,
                'has_season_folder': has_season_folder,
                'in_movie_folder': in_movie_folder,
                'detected_episode': final_episode
            }
        }
    
    @staticmethod
    def format_movie_name(title: str, year: int, optional_info: Optional[str] = None) -> str:
        """
        Format movie filename according to Plex convention
        Example: "Movie Title (2020) [1080p BluRay].mp4"
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = f"{safe_title} ({year})"
        if optional_info:
            filename += f" [{optional_info}]"
        return filename
    
    @staticmethod
    def format_tv_name(show_title: str, season: int, episode: int, 
                      episode_title: Optional[str] = None, year: Optional[int] = None, 
                      optional_info: Optional[str] = None) -> str:
        """
        Format TV episode filename according to Plex convention
        Example: "Show Name (2020) - s01e01 - Episode Title [1080p BluRay].mp4"
        Plex format: ShowName (Year) - sXXeYY - Episode Title [Optional_Info].ext
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '', show_title)
        
        filename = safe_title
        if year:
            filename += f" ({year})"
        # Use lowercase 's' and 'e' as per Plex specification
        filename += f" - s{season:02d}e{episode:02d}"
        
        if episode_title:
            safe_episode_title = re.sub(r'[<>:"/\\|?*]', '', episode_title)
            filename += f" - {safe_episode_title}"
        
        # Add optional info in brackets (ignored by Plex for matching)
        if optional_info:
            filename += f" [{optional_info}]"
        
        return filename
    
    @staticmethod
    def combine_optional_info(filename_info: Optional[str], media_info: Dict[str, Any]) -> Optional[str]:
        """
        Combine filename-extracted info with actual media info from ffmpeg probe
        IMPORTANT: Always uses actual media info (resolution, codecs) over filename claims
        Only uses filename for source info (BluRay, WEB-DL) that can't be detected from file
        """
        info_parts = []
        
        # ALWAYS use resolution from ffmpeg probe (ignores filename claims like "1080p")
        if media_info.get('resolution'):
            info_parts.append(media_info['resolution'])
        
        # Source info from filename ONLY (can't be detected from file metadata)
        if filename_info:
            # Extract source-related keywords from filename info
            source_keywords = ['BLURAY', 'WEB-DL', 'WEBDL', 'WEBRIP', 'HDTV', 'PDTV', 'SDTV', 'BRRIP', 'BDRIP', 'DVD', 'DVDRIP']
            for keyword in source_keywords:
                if keyword in filename_info.upper():
                    if keyword not in ' '.join(info_parts).upper():
                        info_parts.append(keyword)
                    break
        
        # ALWAYS use video codec from ffmpeg probe (ignores filename claims like "x264")
        if media_info.get('video_codec'):
            info_parts.append(media_info['video_codec'])
        
        # ALWAYS use audio codec from ffmpeg probe (ignores filename claims like "AAC")
        if media_info.get('audio_codec'):
            info_parts.append(media_info['audio_codec'])
        
        # Add special tags from filename (can't be detected from file)
        if filename_info:
            special_keywords = ['PROPER', 'REPACK', 'EXTENDED', 'UNRATED', 'DIRECTOR\'S CUT', 'THEATRICAL']
            for keyword in special_keywords:
                if keyword in filename_info.upper():
                    if keyword not in ' '.join(info_parts).upper():
                        info_parts.append(keyword)
        
        return ' '.join(info_parts) if info_parts else None
    
    @staticmethod
    def extract_optional_info(filename: str) -> Optional[str]:
        """
        Extract optional info from filename (quality, source, etc.)
        Looks for patterns like: 1080p, BluRay, WEB-DL, x264, etc.
        """
        # Remove file extension
        name = Path(filename).stem.lower()
        
        # Common quality and source indicators
        optional_patterns = [
            r'1080p', r'720p', r'480p', r'4k', r'2160p',
            r'bluray', r'blu-ray', r'brrip', r'bdrip',
            r'web-dl', r'webdl', r'webrip', r'web',
            r'hdtv', r'pdtv', r'sdtv',
            r'x264', r'x265', r'h264', r'h265', r'hevc',
            r'aac', r'ac3', r'dts', r'mp3',
            r'proper', r'repack', r'extended', r'unrated',
            r'director\'?s?\s?cut', r'theatrical'
        ]
        
        found_info = []
        for pattern in optional_patterns:
            matches = re.findall(rf'\b{pattern}\b', name, re.IGNORECASE)
            for match in matches:
                if match.lower() not in [info.lower() for info in found_info]:
                    found_info.append(match.upper())
        
        return ' '.join(found_info) if found_info else None


def process_optional_info(file_path: Path, namer: 'PlexFileNamer', media_info: Dict[str, Any]) -> Optional[str]:
    """
    Extract optional info from filename, combine with media info, and check for mismatches
    
    Args:
        file_path: Path to the video file
        namer: PlexFileNamer instance
        media_info: Media information from ffmpeg probe
    
    Returns:
        Combined optional info string or None
    """
    filename_optional_info = namer.extract_optional_info(file_path.name)
    combined_optional_info = namer.combine_optional_info(filename_optional_info, media_info)
    
    if combined_optional_info:
        print(f"Optional info: {combined_optional_info}")
        # Show if actual file data differs from filename claims
        check_resolution_mismatch(filename_optional_info, media_info)
    
    return combined_optional_info


def check_resolution_mismatch(filename_optional_info: Optional[str], media_info: Dict[str, Any]) -> None:
    """
    Check if the resolution claimed in the filename matches the actual resolution
    and print a warning if they differ
    
    Args:
        filename_optional_info: Optional info extracted from filename
        media_info: Media information from ffmpeg probe
    """
    if filename_optional_info and media_info.get('resolution'):
        resolution_checks = [
            ('1080P', '1080p'),
            ('720P', '720p'),
            ('4K', '4K'),
            ('2160P', '4K'),
            ('480P', '480p'),
            ('1440P', '1440p')
        ]
        
        for claimed, actual in resolution_checks:
            if claimed in filename_optional_info.upper() and media_info['resolution'] != actual:
                print(f"  Note: File is actually {media_info['resolution']}, not {actual} as filename suggests")
                break


def load_config() -> Dict[str, Any]:
    """
    Load configuration from ~/.plex-renamer.conf if it exists
    
    Returns:
        Dict with configuration values, empty dict if no config file
    """
    config_path = Path.home() / '.plex-renamer.conf'
    config_values = {}
    
    if config_path.exists():
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            # Load default section if it exists
            if 'default' in config:
                defaults = config['default']
                
                # Get all possible config values
                if 'api_key' in defaults:
                    config_values['api_key'] = defaults['api_key']
                if 'default_type' in defaults:
                    config_values['media_type'] = defaults['default_type']
                if 'parentheses_only' in defaults:
                    config_values['parentheses_only'] = defaults.getboolean('parentheses_only')
                if 'create_backups' in defaults:
                    config_values['create_backups'] = defaults.getboolean('create_backups')
                if 'skip_confirmation' in defaults:
                    config_values['skip_confirmation'] = defaults.getboolean('skip_confirmation')
                    
            print(f"📝 Loaded config from: {config_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not parse config file: {e}")
    
    return config_values


def create_backup_file(old_path: Path, new_path: Path) -> None:
    """
    Create or update a backup txt file with the original path/filename for reverting changes
    Preserves the very first original filename even across multiple renames
    
    Args:
        old_path: Current file path before this rename
        new_path: New file path after this rename
    """
    try:
        # Check if there's an existing backup file for the current file
        old_backup_filename = f"{old_path.stem}.original.txt"
        old_backup_path = old_path.parent / old_backup_filename
        
        # Variables to store the true original filename
        true_original_filename = None
        true_original_path = None
        rename_history = []
        
        # If a backup already exists, read the true original filename from it
        if old_backup_path.exists():
            try:
                with open(old_backup_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("Original filename:"):
                            true_original_filename = line.split(":", 1)[1].strip()
                        elif line.startswith("Original full path:"):
                            true_original_path = line.split(":", 1)[1].strip()
                        elif line.startswith("Rename history:"):
                            # Parse existing rename history
                            for history_line in lines[lines.index(line)+1:]:
                                if history_line.strip() and not history_line.startswith("#"):
                                    rename_history.append(history_line.strip())
                print(f"📝 Found existing backup, preserving original: {true_original_filename}")
                # Delete the old backup file as we'll create a new one
                old_backup_path.unlink()
            except Exception as e:
                print(f"⚠️  Warning: Could not read existing backup: {e}")
        
        # If no true original found, use the current old_path as the original
        if not true_original_filename:
            true_original_filename = old_path.name
            true_original_path = str(old_path.absolute())
        
        # Add current rename to history
        rename_history.append(f"{__import__('datetime').datetime.now().isoformat()}: {old_path.name} → {new_path.name}")
        
        # Create new backup filename based on new filename
        backup_filename = f"{new_path.stem}.original.txt"
        backup_path = new_path.parent / backup_filename
        
        # Write backup info to file
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(f"Original filename: {true_original_filename}\n")
            f.write(f"Original full path: {true_original_path}\n")
            f.write(f"Current filename: {new_path.name}\n")
            f.write(f"Last renamed on: {__import__('datetime').datetime.now().isoformat()}\n")
            f.write(f"\nRename history:\n")
            for entry in rename_history[-10:]:  # Keep last 10 renames
                f.write(f"  {entry}\n")
            f.write(f"\n# To revert: mv '{new_path.name}' '{true_original_filename}'\n")
        
        print(f"📝 Backup info saved: {backup_filename}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup file: {e}")


def revert_renames(folder_path: str, dry_run: bool = False) -> None:
    """
    Revert all renamed files in a folder by reading .original.txt backup files
    
    Args:
        folder_path: Path to folder containing backup files
        dry_run: If True, show what would be reverted without actually reverting
    """
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Folder does not exist: {folder_path}")
        return
    
    # Find all .original.txt backup files
    backup_files = list(folder.rglob("*.original.txt"))
    
    if not backup_files:
        print(f"No backup files found in: {folder_path}")
        return
    
    print(f"\nFound {len(backup_files)} backup file(s)")
    print("=" * 60)
    
    # Show what will be reverted
    print("\nFiles that will be reverted:")
    for backup_file in backup_files:
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            original_filename = None
            renamed_filename = None
            
            for line in lines:
                if line.startswith("Original filename:"):
                    original_filename = line.split(":", 1)[1].strip()
                elif line.startswith("Current filename:"):
                    renamed_filename = line.split(":", 1)[1].strip()
                elif line.startswith("Renamed to:") and not renamed_filename:
                    # Handle old format backup files
                    renamed_filename = line.split(":", 1)[1].strip()
            
            if original_filename and renamed_filename:
                print(f"  {renamed_filename} → {original_filename}")
        except:
            print(f"  {backup_file.name} (couldn't read)")
    
    # Confirmation prompt (skip in dry-run mode)
    if not dry_run:
        print(f"\n⚠️  This will revert {len(backup_files)} file(s) and delete their backup files.")
        response = input("Are you sure you want to continue? (y/N): ").strip().lower()
        
        if response not in ['y', 'yes']:
            print("Revert cancelled.")
            return
    
    print("\nProcessing reversions...")
    print("=" * 60)
    
    successful = 0
    failed = 0
    skipped = 0
    
    for backup_file in backup_files:
        print(f"\nProcessing: {backup_file.name}")
        print("-" * 40)
        
        try:
            # Read the backup file
            with open(backup_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse the original filename
            original_filename = None
            renamed_filename = None
            
            for line in lines:
                if line.startswith("Original filename:"):
                    original_filename = line.split(":", 1)[1].strip()
                elif line.startswith("Current filename:"):
                    renamed_filename = line.split(":", 1)[1].strip()
                elif line.startswith("Renamed to:") and not renamed_filename:
                    # Handle old format backup files
                    renamed_filename = line.split(":", 1)[1].strip()
            
            if not original_filename or not renamed_filename:
                print("❌ Invalid backup file format")
                failed += 1
                continue
            
            # Construct file paths
            current_file = backup_file.parent / renamed_filename
            original_file = backup_file.parent / original_filename
            
            if not current_file.exists():
                print(f"❌ Renamed file not found: {renamed_filename}")
                failed += 1
                continue
            
            if original_file.exists():
                print(f"⚠️  Original filename already exists, skipping: {original_filename}")
                skipped += 1
                continue
            
            if dry_run:
                print(f"[DRY RUN] Would revert:")
                print(f"  From: {renamed_filename}")
                print(f"  To:   {original_filename}")
                successful += 1
            else:
                # Perform the revert
                current_file.rename(original_file)
                print(f"✓ Reverted: {renamed_filename} → {original_filename}")
                
                # Remove the backup file after successful revert
                backup_file.unlink()
                print(f"📝 Removed backup file: {backup_file.name}")
                successful += 1
        
        except Exception as e:
            print(f"❌ Error processing {backup_file.name}: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("REVERT SUMMARY")
    print("=" * 60)
    print(f"Total backup files processed: {len(backup_files)}")
    print(f"✓ Successfully reverted: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    if skipped > 0:
        print(f"⚠️  Skipped: {skipped}")
    
    if dry_run:
        print("\n[DRY RUN MODE] No files were actually reverted")
        print("Run without --dry-run to perform actual reversion")


def process_video_file(file_path: str, api_key: Optional[str] = None, media_type: str = "auto", dry_run: bool = False, parentheses_only: bool = False) -> Optional[str]:
    """
    Main function to process a video file:
    1. Extract video duration
    2. Parse filename for title and year
    3. Fetch metadata from TMDb
    4. Generate Plex-compliant filename
    
    Args:
        file_path: Path to the video file
        api_key: TMDb API key (or set TMDB_API_KEY env var)
        media_type: "movie", "tv", or "auto" (auto-detect)
        dry_run: If True, don't actually rename, just return the new path
        parentheses_only: If True, only look for years in parentheses format
    
    Returns:
        New filename following Plex conventions
    """
    
    # Initialize components
    inspector = VideoInspector()
    tmdb = TMDbAPI(api_key)
    namer = PlexFileNamer()
    
    # Get video file info
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return None
    
    print(f"\nProcessing: {file_path.name}")
    print("-" * 50)
    
    # Get detailed media info from ffmpeg probe
    media_info = inspector.get_media_info(str(file_path))
    duration_minutes = media_info['duration'] / 60
    
    # Display media info
    print(f"Video duration: {duration_minutes:.1f} minutes")
    if media_info['resolution']:
        print(f"Resolution: {media_info['resolution']}")
        if media_info.get('raw_resolution'):
            print(f"Raw resolution: {media_info['raw_resolution']}")
    if media_info['video_codec']:
        print(f"Video codec: {media_info['video_codec']}")
    if media_info['audio_codec']:
        print(f"Audio codec: {media_info['audio_codec']}")
    
    # Smart TV show analysis
    tv_analysis = namer.analyze_tv_show(file_path, parentheses_only)
    
    print(f"Parsed title: {tv_analysis['show_name']}")
    if tv_analysis['year']:
        print(f"Parsed year: {tv_analysis['year']}")
    if tv_analysis['season'] and tv_analysis['episode']:
        print(f"Parsed episode: S{tv_analysis['season']:02d}E{tv_analysis['episode']:02d}")
    elif tv_analysis['episode']:
        print(f"Parsed episode: E{tv_analysis['episode']:02d}")
    
    print(f"TV show detected: {tv_analysis['is_tv_show']}")
    
    # Debug info
    debug = tv_analysis['debug_info']
    if debug['detected_episode']:
        print(f"Note: Detected episode number {debug['detected_episode']} in filename")
        if debug['in_movie_folder']:
            print(f"Note: File is in movie folder '{debug['parent_folder']}', treating as movie not TV show")
    
    # Warning for potential TV shows with missing episode numbers
    if tv_analysis['missing_episode_warning']:
        print(f"⚠️  WARNING: File is in season folder '{debug['parent_folder']}' but has no episode number!")
        print(f"   This might be a TV show episode with missing episode info in filename.")
        print(f"   Consider renaming to include episode number (e.g., S{debug['season_from_folder']:02d}E01, E01, etc.)")
    
    # Additional debug info
    if debug['season_from_folder']:
        print(f"Season from folder: {debug['season_from_folder']}")
    if debug['show_name_from_path'] and debug['show_name_from_path'] != tv_analysis['show_name']:
        print(f"Show name from path: {debug['show_name_from_path']}")
    
    # Auto-detect media type if needed - TV analysis takes precedence
    if media_type == "auto":
        media_type = "tv" if tv_analysis['is_tv_show'] else "movie"
        print(f"Detected type: {media_type}")
    elif media_type != "tv" and tv_analysis['is_tv_show']:
        # User forced movie/other type but we detected TV show - warn and override
        print(f"⚠️  WARNING: --type {media_type} specified but detected TV show with S{tv_analysis['season']:02d}E{tv_analysis['episode']:02d}")
        print(f"   Overriding to --type tv for proper TV show processing")
        media_type = "tv"
    
    # Extract individual values for compatibility
    title = tv_analysis['show_name']
    year = tv_analysis['year']
    season = tv_analysis['season']
    episode = tv_analysis['episode']
    
    # Search for metadata
    print(f"\nSearching TMDb for: {title}")
    
    if media_type == "tv":
        # Search for TV show
        show = tmdb.search_tv(title, year)
        if show:
            print(f"Found TV show: {show['name']} ({show.get('first_air_date', 'N/A')[:4]})")
            
            # Get detailed show info
            details = tmdb.get_tv_details(show['id'])
            if details:
                show_year = int(details['first_air_date'][:4]) if details.get('first_air_date') else None
                
                # Get episode details for episode title
                episode_title = None
                if season and episode:
                    episode_details = tmdb.get_episode_details(show['id'], int(season), int(episode))
                    if episode_details and episode_details.get('name'):
                        episode_title = episode_details['name']
                        print(f"Found episode title: {episode_title}")
                
                # Extract optional info from filename and combine with media info
                combined_optional_info = process_optional_info(file_path, namer, media_info)
                
                # Generate new filename
                if season and episode:
                    new_name = namer.format_tv_name(
                        details['name'],
                        int(season),
                        int(episode),
                        episode_title=episode_title,
                        year=show_year,
                        optional_info=combined_optional_info
                    )
                else:
                    # Default to S01E01 if not detected
                    new_name = namer.format_tv_name(
                        details['name'],
                        1, 1,
                        year=show_year,
                        optional_info=combined_optional_info
                    )
            else:
                print("Could not fetch show details")
                return None
        else:
            print("TV show not found in TMDb")
            return None
    
    else:  # movie
        # Search for movie
        movie = tmdb.search_movie(title, year)
        if movie:
            print(f"Found movie: {movie['title']} ({movie.get('release_date', 'N/A')[:4]})")
            
            # Get detailed movie info
            details = tmdb.get_movie_details(movie['id'])
            if details:
                movie_year = int(details['release_date'][:4]) if details.get('release_date') else year or 0
                
                # Extract optional info from filename and combine with media info
                combined_optional_info = process_optional_info(file_path, namer, media_info)
                
                # Generate new filename
                new_name = namer.format_movie_name(details['title'], movie_year, combined_optional_info)
            else:
                print("Could not fetch movie details")
                return None
        else:
            print("Movie not found in TMDb")
            return None
    
    # Add original extension
    new_filename = new_name + file_path.suffix
    
    # Create full path
    new_path = file_path.parent / new_filename
    
    if dry_run:
        print(f"\n[DRY RUN] Would rename:")
        print(f"  From: {file_path.name}")
        print(f"  To:   {new_filename}")
    else:
        print(f"\nSuggested Plex filename: {new_filename}")
        print(f"Full path: {new_path}")
    
    return str(new_path)


def get_video_files(path: str) -> List[Path]:
    """
    Get all video files from a path (file or directory)
    
    Args:
        path: File or directory path
    
    Returns:
        List of video file paths
    """
    video_extensions = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.3g2', '.ts', '.mts',
        '.m2ts', '.vob', '.ogv', '.divx', '.xvid', '.rm', '.rmvb'
    }
    
    path_obj = Path(path)
    video_files = []
    
    if not path_obj.exists():
        print(f"Error: Path does not exist: {path}")
        return []
    
    if path_obj.is_file():
        # Single file
        if path_obj.suffix.lower() in video_extensions:
            video_files.append(path_obj)
    elif path_obj.is_dir():
        # Directory - walk recursively using os.walk (better for network shares)
        try:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in video_extensions:
                        video_files.append(file_path)
        except PermissionError as e:
            print(f"\n⚠️  Permission denied accessing directory: {path}")
            print(f"   Please grant Terminal/VS Code access in System Settings → Privacy & Security → Files and Folders")
            return []
        except Exception as e:
            print(f"Error accessing directory: {e}")
            return []
    return sorted(video_files)


def process_path(path: str, api_key: Optional[str] = None, media_type: str = "auto", 
                 dry_run: bool = False, rename: bool = False, parentheses_only: bool = False,
                 skip_confirmation: bool = False) -> None:
    """
    Process a file or directory of video files
    
    Args:
        path: File or directory path
        api_key: TMDb API key
        media_type: "movie", "tv", or "auto"
        dry_run: Preview mode without renaming
        rename: Actually rename files (ignored if dry_run is True)
        skip_confirmation: Skip confirmation prompt for each rename
    """
    video_files = get_video_files(path)
    
    if not video_files:
        print(f"No video files found in: {path}")
        return
    
    print(f"\nFound {len(video_files)} video file(s)")
    print("=" * 60)
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Processing: {video_file}")
        print("-" * 60)
        
        try:
            new_path = process_video_file(str(video_file), api_key, media_type, dry_run, parentheses_only)
            
            if new_path:
                old_path = Path(video_file)
                new_path = Path(new_path)
                
                if not dry_run and rename:
                    if old_path != new_path:
                        if new_path.exists():
                            print(f"⚠️  Target file already exists, skipping")
                            skipped += 1
                        else:
                            # Ask for confirmation unless skip_confirmation is True
                            should_rename = skip_confirmation
                            if not skip_confirmation:
                                print(f"\nRename this file?")
                                print(f"  From: {old_path.name}")
                                print(f"  To:   {new_path.name}")
                                response = input("Confirm rename? (y/N): ").strip().lower()
                                should_rename = response in ['y', 'yes']
                            
                            if should_rename:
                                # Create backup file before renaming
                                create_backup_file(old_path, new_path)
                                # Perform the rename
                                old_path.rename(new_path)
                                print(f"✓ File renamed successfully")
                                successful += 1
                            else:
                                print("⚠️  Rename skipped by user")
                                skipped += 1
                    else:
                        print("File already has correct name")
                        skipped += 1
                elif dry_run:
                    successful += 1
                else:
                    successful += 1
            else:
                print("❌ Could not determine new filename")
                failed += 1
                
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {len(video_files)}")
    print(f"✓ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    if skipped > 0:
        print(f"⚠️  Skipped: {skipped}")
    
    if dry_run:
        print("\n[DRY RUN MODE] No files were actually renamed")
        print("Run without --dry-run to perform actual renaming")


def main():
    """Command-line interface"""
    import argparse
    
    # Load config file for defaults
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Rename video files according to Plex naming conventions")
    parser.add_argument("path", help="Path to video file or directory")
    parser.add_argument("--api-key", default=config.get('api_key'),
                       help="TMDb API key (or set TMDB_API_KEY env var or use config file)")
    parser.add_argument("--type", choices=["movie", "tv", "auto"], 
                       default=config.get('media_type', 'auto'),
                       help="Media type (default: auto-detect)")
    parser.add_argument("--rename", action="store_true", 
                       help="Actually rename the files (without this, only shows what would be renamed)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview mode - show what would be renamed without actually renaming")
    parser.add_argument("--yes", "-y", action="store_true", dest="skip_confirmation",
                       default=config.get('skip_confirmation', False),
                       help="Skip confirmation prompt for each rename (auto-approve all renames)")
    parser.add_argument("--parentheses-only", action="store_true",
                       default=config.get('parentheses_only', False),
                       help="Only look for years in parentheses format (2004), not - 2004 or space 2004")
    parser.add_argument("--revert", action="store_true",
                       help="Revert all renames in the specified folder using backup files")
    
    args = parser.parse_args()
    
    # Handle revert mode
    if args.revert:
        revert_renames(args.path, args.dry_run)
    else:
        # Process the path (file or directory)
        process_path(args.path, args.api_key, args.type, args.dry_run, args.rename, args.parentheses_only,
                    args.skip_confirmation)


if __name__ == "__main__":
    main()
    