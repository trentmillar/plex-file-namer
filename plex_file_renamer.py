#!/usr/bin/env python3
"""
Plex File Renamer - Inspect video files, fetch metadata, and rename according to Plex conventions
"""

import os
import re
import sys
import configparser
from datetime import datetime
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
    
    # Roman numeral mappings
    ROMAN_TO_NUMBER = {
        'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5',
        'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'
    }
    
    NUMBER_TO_ROMAN = {v: k for k, v in ROMAN_TO_NUMBER.items()}
    
    @staticmethod
    def normalize_title_for_matching(title: str) -> str:
        """
        Normalize a title for matching by converting between Roman numerals and numbers
        Returns both the original and converted version for flexible matching
        """
        title_lower = title.lower().strip()
        
        # Split title into words
        words = title_lower.split()
        if not words:
            return title_lower
        
        # Check if the last word is a Roman numeral or number that could be converted
        last_word = words[-1]
        
        # Convert Roman numeral to number
        if last_word in TMDbAPI.ROMAN_TO_NUMBER:
            converted_words = words[:-1] + [TMDbAPI.ROMAN_TO_NUMBER[last_word]]
            return ' '.join(converted_words)
        
        # Convert number to Roman numeral
        elif last_word in TMDbAPI.NUMBER_TO_ROMAN:
            converted_words = words[:-1] + [TMDbAPI.NUMBER_TO_ROMAN[last_word]]
            return ' '.join(converted_words)
        
        return title_lower
    
    @staticmethod
    def titles_match(search_title: str, api_title: str) -> bool:
        """
        Check if two titles match, considering Roman numeral/number variations
        """
        search_lower = search_title.lower().strip()
        api_lower = api_title.lower().strip()
        
        # Direct match
        if search_lower == api_lower:
            return True
        
        # Try with Roman numeral conversions
        search_normalized = TMDbAPI.normalize_title_for_matching(search_title)
        api_normalized = TMDbAPI.normalize_title_for_matching(api_title)
        
        # Check if normalized versions match
        if search_normalized == api_lower or search_lower == api_normalized:
            return True
        
        # Check if both normalized versions match
        if search_normalized == api_normalized and search_normalized != search_lower:
            return True
        
        return False
    
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
    
    def search_movie(self, title: str, year: Optional[int] = None, duration_minutes: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Search for a movie by title and optional year, with duration matching if multiple results"""
        # Store the search query for exact name matching
        self._last_search_query = title
        
        # Try searching with the original title first
        all_results = []
        search_queries = [title]
        
        # Also try with Roman numeral conversion if applicable
        normalized_title = self.normalize_title_for_matching(title)
        if normalized_title != title.lower():
            # The title has a convertible numeral/number, try the converted version too
            words = title.split()
            last_word = words[-1]
            
            # Convert the last word
            if last_word.lower() in self.ROMAN_TO_NUMBER:
                converted_title = ' '.join(words[:-1] + [self.ROMAN_TO_NUMBER[last_word.lower()]])
            elif last_word in self.NUMBER_TO_ROMAN:
                converted_title = ' '.join(words[:-1] + [self.NUMBER_TO_ROMAN[last_word].upper()])
            else:
                converted_title = None
            
            if converted_title:
                search_queries.append(converted_title)
                print(f"Also searching for: {converted_title}")
        
        # Search with each query
        for query in search_queries:
            params = {
                'api_key': self.api_key,
                'query': query
            }
            if year:
                params['year'] = year
            
            try:
                response = requests.get(f"{self.BASE_URL}/search/movie", params=params)
                response.raise_for_status()
                data = response.json()
                
                if data['results']:
                    # Add results, avoiding duplicates
                    for result in data['results']:
                        if not any(r['id'] == result['id'] for r in all_results):
                            all_results.append(result)
            except requests.exceptions.RequestException as e:
                print(f"Error searching for movie with query '{query}': {e}")
        
        if all_results:
            if duration_minutes is not None:
                return self._match_by_duration(all_results, duration_minutes, "movie")
            else:
                return all_results[0]
        
        return None
    
    def search_tv(self, title: str, year: Optional[int] = None, duration_minutes: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Search for a TV show by title and optional year, with duration matching if multiple results"""
        # Store the search query for exact name matching
        self._last_search_query = title
        
        # Try searching with the original title first
        all_results = []
        search_queries = [title]
        
        # Also try with Roman numeral conversion if applicable
        normalized_title = self.normalize_title_for_matching(title)
        if normalized_title != title.lower():
            # The title has a convertible numeral/number, try the converted version too
            words = title.split()
            last_word = words[-1]
            
            # Convert the last word
            if last_word.lower() in self.ROMAN_TO_NUMBER:
                converted_title = ' '.join(words[:-1] + [self.ROMAN_TO_NUMBER[last_word.lower()]])
            elif last_word in self.NUMBER_TO_ROMAN:
                converted_title = ' '.join(words[:-1] + [self.NUMBER_TO_ROMAN[last_word].upper()])
            else:
                converted_title = None
            
            if converted_title:
                search_queries.append(converted_title)
                print(f"Also searching for: {converted_title}")
        
        # Search with each query
        for query in search_queries:
            params = {
                'api_key': self.api_key,
                'query': query
            }
            if year:
                params['first_air_date_year'] = year
            
            try:
                response = requests.get(f"{self.BASE_URL}/search/tv", params=params)
                response.raise_for_status()
                data = response.json()
                
                if data['results']:
                    # Add results, avoiding duplicates
                    for result in data['results']:
                        if not any(r['id'] == result['id'] for r in all_results):
                            all_results.append(result)
            except requests.exceptions.RequestException as e:
                print(f"Error searching for TV show with query '{query}': {e}")
        
        if all_results:
            if duration_minutes is not None:
                return self._match_by_duration(all_results, duration_minutes, "tv")
            else:
                return all_results[0]
        
        # If no results, try simplified search by removing common subtitle words
        if not all_results:
            # Common words that might be added to show titles that TMDb doesn't include
            # Note: 'extended' removed as it's typically a movie edition, not a TV show subtitle
            subtitle_words = ['omnibus', 'special', 'extra', 'highlights', 'compilation']
            
            # Try removing each subtitle word
            for word in subtitle_words:
                if word in title.lower():
                    simple_title = title.replace(word.title(), '').replace(word.lower(), '').strip()
                    # Clean up extra spaces
                    simple_title = ' '.join(simple_title.split())
                    
                    if simple_title and simple_title != title:
                        simple_params = {
                            'api_key': self.api_key,
                            'query': simple_title
                        }
                        if year:
                            simple_params['first_air_date_year'] = year
                        
                        try:
                            simple_response = requests.get(f"{self.BASE_URL}/search/tv", params=simple_params)
                            simple_response.raise_for_status()
                            simple_data = simple_response.json()
                            
                            if simple_data['results']:
                                if duration_minutes is not None:
                                    return self._match_by_duration(simple_data['results'], duration_minutes, "tv")
                                else:
                                    return simple_data['results'][0]
                        except requests.exceptions.RequestException as e:
                            print(f"Error searching for simplified TV show: {e}")
        
        return None
    
    def find_episode_by_date(self, tv_id: int, target_date: str, part_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Find TV episode that aired on a specific date by searching through seasons
        
        Args:
            tv_id: TMDb TV show ID
            target_date: Date in YYYY-MM-DD format
            part_number: Optional part number for multi-part episodes (1, 2, etc.)
            
        Returns:
            Dict with episode info including season_number, episode_number, episode_title
        """
        try:
            # First get TV show details to know how many seasons exist
            tv_details = self.get_tv_details(tv_id)
            if not tv_details:
                return None
            
            total_seasons = tv_details.get('number_of_seasons', 0)
            print(f"Searching for episode aired on {target_date} across {total_seasons} seasons...")
            
            # Search through recent seasons first (most common case)
            # For long-running shows like Coronation Street, start from recent seasons
            search_order = list(range(max(1, total_seasons - 10), total_seasons + 1))  # Last 10 seasons
            search_order.reverse()  # Start with most recent
            
            # Add remaining seasons if not found in recent ones
            remaining_seasons = [s for s in range(1, total_seasons + 1) if s not in search_order]
            search_order.extend(remaining_seasons)
            
            for season_num in search_order:
                print(f"  Checking season {season_num}...")
                
                try:
                    response = requests.get(
                        f"{self.BASE_URL}/tv/{tv_id}/season/{season_num}",
                        params={'api_key': self.api_key, 'language': 'en-US'}
                    )
                    response.raise_for_status()
                    season_data = response.json()
                    
                    episodes = season_data.get('episodes', [])
                    matching_episodes = []
                    
                    # First, collect all episodes that aired on the target date
                    for episode in episodes:
                        episode_air_date = episode.get('air_date')
                        if episode_air_date == target_date:
                            matching_episodes.append(episode)
                    
                    # If we're looking for a specific part number, also check episodes that aired the day after 
                    # (common for multi-part episodes where Part 2 airs the next day)
                    if part_number:
                        from datetime import datetime, timedelta
                        try:
                            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                            next_day = (target_datetime + timedelta(days=1)).strftime('%Y-%m-%d')
                            
                            for episode in episodes:
                                episode_air_date = episode.get('air_date')
                                episode_title = episode.get('name', '')
                                # Check if this episode aired the next day but has the target date in its title
                                if episode_air_date == next_day:
                                    # Check if the episode title contains the target date
                                    target_date_formats = [
                                        target_date,  # 2015-09-14
                                        target_date.replace('-', ' '),  # 2015 09 14
                                        f"Sep 14 2015",  # Mon Sep 14 2015 format
                                    ]
                                    for date_format in target_date_formats:
                                        if date_format in episode_title:
                                            matching_episodes.append(episode)
                                            break
                        except ValueError:
                            pass  # Invalid date format, skip this check
                    
                    if not matching_episodes:
                        continue
                    
                    
                    # If we have a part number, try to find the matching part
                    if part_number:
                        for episode in matching_episodes:
                            episode_title = episode.get('name', '')
                            # Look for part numbers in episode titles
                            part_patterns = [
                                rf'Part\s*{part_number}\b',      # "Part 2", "Part2"
                                rf'Pt\s*{part_number}\b',       # "Pt 2", "Pt2"  
                                rf'P{part_number}\b',           # "P2"
                                rf'\bPart\s*{part_number}',     # "Part 2"
                                rf'\({part_number}\)',          # "(2)"
                            ]
                            
                            for pattern in part_patterns:
                                if re.search(pattern, episode_title, re.IGNORECASE):
                                    print(f"  ✓ Found episode with part {part_number}: S{season_num:02d}E{episode['episode_number']:02d} - {episode.get('name', 'Unknown')}")
                                    return {
                                        'season_number': season_num,
                                        'episode_number': episode['episode_number'],
                                        'episode_title': episode.get('name'),
                                        'air_date': episode_air_date,
                                        'overview': episode.get('overview'),
                                        'runtime': episode.get('runtime')
                                    }
                    
                    # If no part number specified or only one episode found, return the first one
                    episode = matching_episodes[0]
                    print(f"  ✓ Found episode: S{season_num:02d}E{episode['episode_number']:02d} - {episode.get('name', 'Unknown')}")
                    return {
                        'season_number': season_num,
                        'episode_number': episode['episode_number'],
                        'episode_title': episode.get('name'),
                        'air_date': episode_air_date,
                        'overview': episode.get('overview'),
                        'runtime': episode.get('runtime')
                    }
                            
                except requests.exceptions.RequestException as e:
                    print(f"  Error fetching season {season_num}: {e}")
                    continue
            
            print(f"  No episode found for date {target_date}")
            return None
            
        except Exception as e:
            print(f"Error finding episode by date: {e}")
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
    
    def _match_by_duration(self, results: List[Dict[str, Any]], duration_minutes: float, media_type: str) -> Optional[Dict[str, Any]]:
        """Shared logic to match search results by duration with improved matching logic"""
        if not results:
            return None
        
        # If only one result, return it
        if len(results) == 1:
            return results[0]
        
        # Multiple results - try to match by duration
        print(f"Found {len(results)} potential matches, checking durations...")
        
        # Collect all candidates with their durations
        candidates = []
        for item in results[:5]:  # Check top 5 results
            item_duration = None
            
            if media_type == "movie":
                details = self.get_movie_details(item['id'])
                if details and details.get('runtime'):
                    item_duration = details['runtime']
            else:  # TV show
                details = self.get_tv_details(item['id'])
                if details and details.get('episode_run_time'):
                    episode_runtimes = details['episode_run_time']
                    if episode_runtimes:
                        item_duration = episode_runtimes[0]  # Use most common runtime
            
            if item_duration:
                title = item.get('title') or item.get('name', 'Unknown')
                year = (item.get('release_date') or item.get('first_air_date', 'N/A'))[:4]
                duration_diff = abs(duration_minutes - item_duration)
                
                print(f"  {title} ({year}): {item_duration} min (diff: {duration_diff:.1f})")
                
                candidates.append({
                    'item': item,
                    'duration': item_duration,
                    'duration_diff': duration_diff,
                    'title': title,
                    'year': year
                })
        
        if not candidates:
            print("No duration information found, using first result")
            return results[0]
        
        # Get the search query to determine exact name matches
        # We need to extract the original search query to compare against titles
        search_query = None
        if hasattr(self, '_last_search_query'):
            search_query = self._last_search_query
        
        # Step 1: Find all exact name matches (case-insensitive, with Roman numeral support)
        exact_name_matches = []
        for candidate in candidates:
            # Check if this is an exact match using Roman numeral-aware matching
            if search_query and self.titles_match(search_query, candidate['title']):
                exact_name_matches.append(candidate)
        
        # Step 2: If we have exact name matches, prioritize them
        if exact_name_matches:
            print(f"Found {len(exact_name_matches)} exact name match(es)")
            
            # First check if any exact match has duration within +/- 2 minutes
            for candidate in exact_name_matches:
                if candidate['duration_diff'] <= 2.0:
                    print(f"✓ Exact name match with acceptable duration: {candidate['title']} (diff: {candidate['duration_diff']:.1f} min)")
                    return candidate['item']
            
            # If no exact match within 2 minutes, find exact match with closest higher duration
            higher_exact_matches = [c for c in exact_name_matches if c['duration'] >= duration_minutes]
            if higher_exact_matches:
                # Sort by duration (ascending) to get the closest higher duration
                higher_exact_matches.sort(key=lambda c: c['duration'])
                best_match = higher_exact_matches[0]
                print(f"✓ Exact name match with higher duration: {best_match['title']} ({best_match['duration']} min, +{best_match['duration'] - duration_minutes:.1f} min)")
                return best_match['item']
            
            # If no higher duration exact matches, use the closest exact match
            exact_name_matches.sort(key=lambda c: c['duration_diff'])
            best_match = exact_name_matches[0]
            print(f"✓ Best exact name match (lower duration): {best_match['title']} (diff: {best_match['duration_diff']:.1f} min)")
            return best_match['item']
        
        # Step 3: No exact name matches - fall back to duration-based matching
        print("No exact name matches found, using duration-based matching")
        
        # Find the match with duration higher than file duration but closest to it
        higher_duration_candidates = [c for c in candidates if c['duration'] >= duration_minutes]
        if higher_duration_candidates:
            # Sort by duration (ascending) to get the closest higher duration
            higher_duration_candidates.sort(key=lambda c: c['duration'])
            best_match = higher_duration_candidates[0]
            print(f"✓ Best higher duration match: {best_match['title']} ({best_match['duration']} min, +{best_match['duration'] - duration_minutes:.1f} min)")
            return best_match['item']
        
        # Step 4: Fallback to closest duration match (even if lower)
        candidates.sort(key=lambda c: c['duration_diff'])
        best_match = candidates[0]
        print(f"✓ Closest duration match: {best_match['title']} (diff: {best_match['duration_diff']:.1f} min)")
        return best_match['item']


class PatternMatcher:
    """Advanced pattern matching system for complex file structures"""
    
    # Month mappings
    MONTH_MAPPINGS = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
        '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug', 
        '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec',
        '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr',
        '5': 'May', '6': 'Jun', '7': 'Jul', '8': 'Aug',
        '9': 'Sep'
    }
    
    MONTH_REVERSE = {v: k.zfill(2) for k, v in MONTH_MAPPINGS.items() if len(k) <= 2}
    
    @staticmethod
    def parse_pattern_file(file_path: Path, pattern: str, root_folder: Path) -> Optional[Dict[str, Any]]:
        """
        Parse a file using a custom pattern
        
        Args:
            file_path: Path to the video file
            pattern: Pattern string with placeholders
            root_folder: Root folder to calculate relative path from
            
        Returns:
            Dict with extracted information or None if no match
        """
        try:
            # Get relative path from root folder
            rel_path = file_path.relative_to(root_folder)
            path_parts = list(rel_path.parts)
            
            # Parse the pattern
            pattern_parts = pattern.split('/')
            
            print(f"  Debug: Path parts: {path_parts}")
            print(f"  Debug: Pattern parts: {pattern_parts}")
            
            # Allow flexible pattern matching - pattern can be shorter than path
            if len(pattern_parts) > len(path_parts):
                print(f"  Debug: Pattern has more parts ({len(pattern_parts)}) than path ({len(path_parts)})")
                return None
            
            extracted = {}
            
            for i, (path_part, pattern_part) in enumerate(zip(path_parts, pattern_parts)):
                # Handle file extension
                original_path_part = path_part
                if i == len(path_parts) - 1:  # Last part (filename)
                    path_part = Path(path_part).stem  # Remove extension
                    if pattern_part.endswith('.ext'):
                        pattern_part = pattern_part[:-4]  # Remove .ext
                
                print(f"  Debug: Matching '{path_part}' against pattern '{pattern_part}'")
                
                # Special handling for complex filename patterns with multiple segments
                if i == len(path_parts) - 1 and ('{' in pattern_part or pattern_part.count(' ') > 0 or pattern_part.count('.') > 0):
                    # This is a complex filename pattern, try to parse it as segments
                    result = PatternMatcher._match_complex_filename_pattern(path_part, pattern_part)
                else:
                    result = PatternMatcher._match_pattern_part(path_part, pattern_part)
                
                if result is None:
                    print(f"  Debug: No match for '{path_part}' with pattern '{pattern_part}'")
                    return None
                else:
                    print(f"  Debug: Match result: {result}")
                
                extracted.update(result)
            
            # Post-process extracted data
            final_result = PatternMatcher._process_extracted_data(extracted)
            print(f"  Debug: Final extracted data: {final_result}")
            return final_result
            
        except Exception as e:
            print(f"Pattern matching error: {e}")
            return None
    
    @staticmethod
    def _match_pattern_part(text: str, pattern: str) -> Optional[Dict[str, Any]]:
        """Match a single part of the pattern with support for negative patterns (?suffix)"""
        
        # Check for negative pattern (ignore extracted value)
        is_negative = pattern.endswith('?')
        if is_negative:
            pattern = pattern[:-1]  # Remove the ? suffix
            
        # Make pattern matching case insensitive
        pattern_upper = pattern.upper()
        
        if pattern_upper == 'IGNORE':
            return {}
        
        if pattern_upper == 'SHOW_NAME':
            # Clean up show name
            show_name = re.sub(r'[._-]+', ' ', text).strip()
            if is_negative:
                return {'ignored_show_name': show_name}  # Mark as ignored
            return {'show_name': show_name}
        
        if pattern_upper == 'TITLE':
            # Clean up title
            title = re.sub(r'[._-]+', ' ', text).strip()
            if is_negative:
                return {'ignored_title': title}  # Mark as ignored
            return {'title': title}
        
        if pattern_upper.startswith('DATE_FORMAT') or ('{' in pattern_upper and '}' in pattern_upper):
            # First try to parse just the date
            date_result = PatternMatcher._parse_date_format(text, pattern)
            
            # If we got a date result, check if there's additional text after it (like part numbers)
            if date_result and 'air_date' in date_result:
                # Look for part numbers in the remaining text after the date
                part_patterns = [
                    r'[-\s]*PT\s*(\d+)',      # -PT 2, PT2
                    r'[-\s]*Part\s*(\d+)',    # -Part 2, Part2
                    r'[-\s]*P\s*(\d+)',       # -P2
                ]
                
                print(f"    Debug: Looking for part number in text: '{text}'")
                for part_pattern in part_patterns:
                    part_match = re.search(part_pattern, text, re.IGNORECASE)
                    if part_match:
                        date_result['part_number'] = int(part_match.group(1))
                        print(f"    Debug: Extracted part number from date pattern: {date_result['part_number']}")
                        break
                else:
                    print(f"    Debug: No part number found in text: '{text}'")
            
            if date_result and is_negative:
                # Mark all date components as ignored
                ignored_result = {}
                for key, value in date_result.items():
                    ignored_result[f'ignored_{key}'] = value
                return ignored_result
            return date_result
        
        # Literal match (case insensitive) - allow flexible separators
        if pattern.lower() == text.lower():
            return {}
        
        # Handle flexible separators (spaces, dots, dashes, underscores)
        pattern_normalized = re.sub(r'[.\s_-]+', ' ', pattern.lower()).strip()
        text_normalized = re.sub(r'[.\s_-]+', ' ', text.lower()).strip()
        if pattern_normalized == text_normalized:
            return {}
        
        return None
    
    @staticmethod
    def _match_complex_filename_pattern(filename: str, pattern: str) -> Optional[Dict[str, Any]]:
        """Match complex filename patterns like '{TITLE?}.{DD-MM-YY}' against 'Corrie.18.12.17'"""
        
        # Split pattern into segments based on separators
        # Pattern: {TITLE?}.{DD-MM-YY}
        # Filename: Corrie.18.12.17
        
        import re
        
        # Create a regex pattern from the template
        regex_pattern = pattern
        
        # Replace pattern placeholders with regex groups
        placeholder_map = {}
        placeholder_counter = 0
        
        # Find all placeholders like {TITLE?}, {DD-MM-YY}, etc.
        placeholders = re.findall(r'\{([^}]+)\}', pattern)
        
        for placeholder in placeholders:
            placeholder_counter += 1
            group_name = f"group{placeholder_counter}"
            placeholder_map[group_name] = placeholder
            
            # Replace the placeholder with a regex group
            if placeholder.endswith('?'):
                # Negative pattern - match anything
                regex_pattern = regex_pattern.replace(f'{{{placeholder}}}', f'(?P<{group_name}>[^.\\s_-]+)')
            elif any(date_format in placeholder.upper() for date_format in ['DD-MM-YY', 'MM-DD-YY', 'YYYY-MM-DD']):
                # Date pattern - match digits and separators, but allow capturing the full date portion without greedy matching
                regex_pattern = regex_pattern.replace(f'{{{placeholder}}}', f'(?P<{group_name}>\\d{{1,2}}[.-]\\d{{1,2}}[.-]\\d{{2,4}})')
            else:
                # Other patterns - match word characters
                regex_pattern = regex_pattern.replace(f'{{{placeholder}}}', f'(?P<{group_name}>[^.\\s_-]+)')
        
        # Escape literal dots in the pattern
        regex_pattern = regex_pattern.replace('.', '\\.')
        
        print(f"    Debug: Regex pattern: {regex_pattern}")
        
        # Try to match the main pattern
        match = re.match(regex_pattern, filename)
        if not match:
            return None
        
        # Check if there's additional content after the pattern (like .PT2, .Part2, etc.)
        matched_text = match.group(0)
        remaining_text = filename[len(matched_text):]
        part_number = None
        
        
        if remaining_text:
            # Look for part numbers in various formats
            part_patterns = [
                r'[-\s]*PT\s*(\d+)',      # -PT1, -PT 2, PT2
                r'[-\s]*Part\s*(\d+)',    # -Part1, -Part 2, Part2
                r'[-\s]*P\s*(\d+)',       # -P1, -P2, P2
                r'\.PT(\d+)',             # .PT1, .PT2
                r'\.Part\s*(\d+)',        # .Part1, .Part 2
                r'\.P(\d+)',              # .P1, .P2
                r'\sPart\s*(\d+)',        # Part 1, Part 2
                r'\sPT(\d+)',             # PT1, PT2
            ]
            
            for part_pattern in part_patterns:
                part_match = re.search(part_pattern, remaining_text, re.IGNORECASE)
                if part_match:
                    part_number = int(part_match.group(1))
                    break
        
        # Extract matched groups and process them
        extracted = {}
        for group_name, placeholder in placeholder_map.items():
            value = match.group(group_name)
            print(f"    Debug: Extracted {placeholder} = {value}")
            
            # Process the placeholder
            if placeholder.endswith('?'):
                # Negative pattern - mark as ignored
                base_placeholder = placeholder[:-1]
                if base_placeholder.upper() == 'TITLE':
                    extracted['ignored_title'] = value
                elif base_placeholder.upper() == 'SHOW_NAME':
                    extracted['ignored_show_name'] = value
            elif any(date_format in placeholder.upper() for date_format in ['DD-MM-YY', 'MM-DD-YY', 'YYYY-MM-DD']):
                # Parse date
                date_result = PatternMatcher._parse_date_format(value, f'{{{placeholder}}}')
                if date_result:
                    extracted.update(date_result)
            else:
                # Regular extraction
                if placeholder.upper() == 'TITLE':
                    extracted['title'] = value
                elif placeholder.upper() == 'SHOW_NAME':
                    extracted['show_name'] = value
        
        # Add part number if found
        if part_number:
            extracted['part_number'] = part_number
        
        return extracted
    
    @staticmethod
    def _parse_date_format(text: str, pattern: str) -> Optional[Dict[str, Any]]:
        """Parse date format patterns like DATE_FORMAT{YEAR}, {MM-DD-YYYY}, or direct date patterns"""
        
        # Extract the format specification
        if '{' in pattern and '}' in pattern:
            format_spec = pattern[pattern.find('{')+1:pattern.find('}')]
        else:
            # Try to auto-detect date format
            return PatternMatcher._auto_detect_date(text)
        
        # Handle specific date components
        if format_spec == 'YEAR':
            if re.match(r'^\d{4}$', text):
                return {'year': int(text)}
        
        elif format_spec == 'MONTH:THREE_LETTER':
            if text in PatternMatcher.MONTH_REVERSE:
                return {'month': PatternMatcher.MONTH_REVERSE[text]}
        
        elif format_spec == 'DAY:NUMBER':
            if re.match(r'^\d{1,2}$', text):
                return {'day': text.zfill(2)}
        
        # Handle full date patterns
        else:
            return PatternMatcher._parse_full_date(text, format_spec)
        
        return None
    
    @staticmethod
    def _parse_full_date(text: str, format_spec: str) -> Optional[Dict[str, Any]]:
        """Parse full date strings like M-DD-YY or YYYY-MM-DD"""
        
        # Common date patterns (including multi-part episodes)
        date_patterns = [
            # YYYY-MM-DD variations
            (r'^(\d{4})[-.\s](\d{1,2})[-.\s](\d{1,2})$', 'YYYY-MM-DD'),
            # DD-MM-YYYY variations  
            (r'^(\d{1,2})[-.\s](\d{1,2})[-.\s](\d{4})$', 'DD-MM-YYYY'),
            # DD-MM-YY with PT suffix (e.g., "03-04-13 PT1" or "03-04-13 pt1")
            (r'^(\d{1,2})[-.\s](\d{1,2})[-.\s](\d{2})\s+[Pp][Tt](\d+)$', 'DD-MM-YY-PT'),
            # DD-MM-YY basic format (e.g., "30-07-09")
            (r'^(\d{1,2})[-.\s](\d{1,2})[-.\s](\d{2})$', 'DD-MM-YY'),
            # M-DD-YY variations
            (r'^(\d{1,2})[-.\s](\d{1,2})[-.\s](\d{2})$', 'M-DD-YY'),
            # MM-DD-YYYY variations
            (r'^(\d{1,2})[-.\s](\d{1,2})[-.\s](\d{4})$', 'MM-DD-YYYY'),
        ]
        
        for pattern_regex, date_type in date_patterns:
            match = re.match(pattern_regex, text)
            if match:
                groups = match.groups()
                
                if date_type == 'YYYY-MM-DD':
                    year, month, day = groups
                elif date_type == 'DD-MM-YYYY':
                    day, month, year = groups
                elif date_type == 'DD-MM-YY':
                    day, month, year = groups
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                elif date_type == 'M-DD-YY':
                    month, day, year = groups
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                elif date_type == 'MM-DD-YYYY':
                    month, day, year = groups
                elif date_type == 'DD-MM-YY-PT':
                    day, month, year, part_num = groups
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                else:
                    # Default case: try to guess based on the format_spec parameter or number of groups
                    if len(groups) == 3:
                        # Check if format_spec hints at the order
                        if format_spec and 'DD-MM' in format_spec.upper():
                            day, month, year = groups
                        elif format_spec and 'MM-DD' in format_spec.upper():
                            month, day, year = groups
                        else:
                            # Default to DD-MM-YY
                            day, month, year = groups
                        
                        # Handle 2-digit years
                        if len(str(year)) == 2:
                            year = f"20{year}" if int(year) < 50 else f"19{year}"
                    else:
                        # Can't parse this date format
                        continue
                
                # Validate date
                try:
                    datetime(int(year), int(month), int(day))
                    result = {
                        'year': int(year),
                        'month': month.zfill(2),
                        'day': day.zfill(2),
                        'air_date': f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    }
                    
                    # Add part number if this is a multi-part episode
                    if date_type == 'DD-MM-YY-PT':
                        result['part_number'] = int(part_num)
                    
                    return result
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def _auto_detect_date(text: str) -> Optional[Dict[str, Any]]:
        """Auto-detect date format from text"""
        return PatternMatcher._parse_full_date(text, 'auto')
    
    @staticmethod
    def _process_extracted_data(extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process extracted data"""
        
        # If we have date components, create air_date
        if 'year' in extracted and 'month' in extracted and 'day' in extracted:
            if 'air_date' not in extracted:
                year = extracted['year']
                month = extracted['month']
                day = extracted['day']
                extracted['air_date'] = f"{year}-{month}-{day}"
        
        # Mark as date-based TV show if we have air_date
        if 'air_date' in extracted:
            extracted['is_date_based'] = True
            extracted['is_tv_show'] = True
        
        return extracted


class PlexFileNamer:
    """Format filenames according to Plex naming conventions"""
    
    @staticmethod
    def is_already_formatted(file_path: Path) -> bool:
        """
        Check if file is already in proper Plex format with TMDb ID
        Works for movies, TV shows, and date-based content
        Movie: "Title (YYYY) {tmdb-123} [optional].ext"
        TV: "Title (YYYY) {tmdb-123} - s01e01 - Episode [optional].ext"
        Date: "Title (YYYY) {tmdb-123} - YYYY-MM-DD [optional].ext"
        """
        filename = file_path.stem
        
        # Must have year in parentheses
        if not re.search(r'\s\(\d{4}\)', filename):
            return False
        
        # Must have TMDb ID
        if not re.search(r'\{tmdb-\d+\}', filename):
            return False
        
        # Check for backup file existence
        backup_filename = f"{filename}.original.txt"
        backup_path = file_path.parent / backup_filename
        
        return backup_path.exists()
    
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
            # Only look for years in parentheses: " (2004)" with optional text after
            trailing_year_patterns = [
                r'\s*\((\d{4})\)(?:\s*[-–]\s*.*)?$',      # " (2004)" or " (2004) - anything"
            ]
        else:
            # Look for all year patterns including dot-separated
            trailing_year_patterns = [
                r'\.(\d{4})(?:\.|$)',       # .1999. or .1999 at end (dot-separated)
                r'\s*\((\d{4})\)(?:\s*[-–]\s*.*)?$',      # " (2004)" or " (2004) - anything"
                r'\s*-\s*(\d{4})(?:\s*[-–]\s*.*)?$',      # " - 2004" or " - 2004 - anything"
                r'\s+(\d{4})(?:\s+[-–]\s*.*)?$',          # " 2004" or " 2004 - anything"  
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
    def format_movie_name(title: str, year: int, tmdb_id: Optional[int] = None, edition: Optional[str] = None, optional_info: Optional[str] = None) -> str:
        """
        Format movie filename according to Plex convention
        Example: "Movie Title (2020) {tmdb-123} {edition-Director's Cut} [1080p BluRay].mp4"
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = f"{safe_title} ({year})"
        if tmdb_id:
            filename += f" {{tmdb-{tmdb_id}}}"
        if edition:
            # Truncate edition name to 32 characters as per Plex requirements
            safe_edition = edition[:32] if len(edition) > 32 else edition
            filename += f" {{edition-{safe_edition}}}"
        if optional_info:
            filename += f" [{optional_info}]"
        return filename
    
    @staticmethod
    def format_tv_name(show_title: str, season: int, episode: int, 
                      episode_title: Optional[str] = None, year: Optional[int] = None, 
                      tmdb_id: Optional[int] = None, optional_info: Optional[str] = None) -> str:
        """
        Format TV episode filename according to Plex convention
        Example: "Show Name (2020) {tmdb-123} - s01e01 - Episode Title [1080p BluRay].mp4"
        Plex format: ShowName (Year) {tmdb-id} - sXXeYY - Episode Title [Optional_Info].ext
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '', show_title)
        
        filename = safe_title
        if year:
            filename += f" ({year})"
        if tmdb_id:
            filename += f" {{tmdb-{tmdb_id}}}"
        # Use lowercase 's' and 'e' as per Plex specification
        filename += f" - s{season:02d}e{episode:02d}"
        
        if episode_title:
            # Remove broadcast times like (19:00) from episode titles
            safe_episode_title = episode_title
            safe_episode_title = re.sub(r'\s*\(\d{1,2}:\d{2}\)', '', safe_episode_title)  # Remove (19:00), (20:30), etc.
            
            # Then remove other illegal characters
            safe_episode_title = re.sub(r'[<>:"/\\|?*]', '', safe_episode_title)
            filename += f" - {safe_episode_title}"
        
        # Add optional info in brackets (ignored by Plex for matching)
        if optional_info:
            filename += f" [{optional_info}]"
        
        return filename
    
    @staticmethod
    def format_date_based_tv_name(show_title: str, air_date: str, 
                                 episode_title: Optional[str] = None, year: Optional[int] = None,
                                 tmdb_id: Optional[int] = None, optional_info: Optional[str] = None, 
                                 part_number: Optional[int] = None) -> str:
        """
        Format date-based TV episode filename according to Plex convention
        Example: "Show Name (2020) {tmdb-123} - 2011-11-15 - Episode Title [1080p BluRay].mp4"
        Plex format: ShowName (Year) {tmdb-id} - YYYY-MM-DD - Episode Title [Optional_Info].ext
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '', show_title)
        
        filename = safe_title
        if year:
            filename += f" ({year})"
        if tmdb_id:
            filename += f" {{tmdb-{tmdb_id}}}"
        
        # Use the air date in YYYY-MM-DD format
        filename += f" - {air_date}"
        
        if episode_title:
            # Remove broadcast times like (19:00) from episode titles
            safe_episode_title = episode_title
            safe_episode_title = re.sub(r'\s*\(\d{1,2}:\d{2}\)', '', safe_episode_title)  # Remove (19:00), (20:30), etc.
            
            # Then remove other illegal characters
            safe_episode_title = re.sub(r'[<>:"/\\|?*]', '', safe_episode_title)
            filename += f" - {safe_episode_title}"
        
        # Add part number for multi-part episodes
        if part_number:
            filename += f" - pt{part_number}"
        
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
        
        # Add special tags from filename (can't be detected from file, excluding editions)
        if filename_info:
            special_keywords = ['PROPER', 'REPACK']
            for keyword in special_keywords:
                if keyword in filename_info.upper():
                    if keyword not in ' '.join(info_parts).upper():
                        info_parts.append(keyword)
        
        return ' '.join(info_parts) if info_parts else None
    
    @staticmethod
    def extract_edition_info(filename: str) -> Optional[str]:
        """
        Extract edition info from filename for Plex {edition-name} format
        Returns the edition name (without {edition-} wrapper)
        """
        # Remove file extension
        name = Path(filename).stem.lower()
        
        # Edition patterns - these will be moved to {edition-} format
        # Order matters: more specific patterns should come first
        # Use [.\s]* to match dots, spaces, or no separator
        edition_patterns = [
            (r'director\'?s?[.\s]*cut', "Director's Cut"),
            (r'collector\'?s?[.\s]*edition', "Collector's Edition"),
            (r'special[.\s]+edition', 'Special Edition'),  # Must come before 'special'
            (r'anniversary[.\s]*edition', 'Anniversary Edition'),
            (r'ultimate[.\s]*edition', 'Ultimate Edition'),
            (r'deluxe[.\s]*edition', 'Deluxe Edition'),
            (r'theatrical[.\s]*(?:cut|version|release)?', 'Theatrical'),
            (r'extended[.\s]*(?:cut|version|edition)?', 'Extended'),
            (r'unrated[.\s]*(?:cut|version|edition)?', 'Unrated'),
            (r'criterion[.\s]*(?:collection)?', 'Criterion'),
            (r'final[.\s]*cut', 'Final Cut'),
            (r'international[.\s]*(?:cut|version)', 'International'),
            (r'remastered', 'Remastered'),
            # Additional special edition types (put standalone words after compound words)
            (r'omnibus', 'Omnibus'),
            (r'special', 'Special'),  # Now after "Special Edition"
            (r'extra', 'Extra'),
            (r'highlights', 'Highlights'),
            (r'compilation', 'Compilation'),
        ]
        
        for pattern, edition_name in edition_patterns:
            if re.search(rf'\b{pattern}\b', name, re.IGNORECASE):
                return edition_name
        
        return None
    
    @staticmethod
    def extract_optional_info(filename: str) -> Optional[str]:
        """
        Extract optional info from filename (quality, source, etc.)
        Excludes edition info which is handled separately
        """
        # Remove file extension
        name = Path(filename).stem.lower()
        
        # Quality and source indicators (excluding editions)
        optional_patterns = [
            r'1080p', r'720p', r'480p', r'4k', r'2160p',
            r'bluray', r'blu-ray', r'brrip', r'bdrip',
            r'web-dl', r'webdl', r'webrip', r'web',
            r'hdtv', r'pdtv', r'sdtv',
            r'x264', r'x265', r'h264', r'h265', r'hevc',
            r'aac', r'ac3', r'dts', r'mp3',
            r'proper', r'repack'
        ]
        
        found_info = []
        for pattern in optional_patterns:
            matches = re.findall(rf'\b{pattern}\b', name, re.IGNORECASE)
            for match in matches:
                normalized = match.upper()
                if normalized not in found_info:
                    found_info.append(normalized)
        
        return ' '.join(found_info) if found_info else None


def process_optional_info(file_path: Path, namer: 'PlexFileNamer', media_info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract edition and optional info from filename, combine with media info
    
    Args:
        file_path: Path to the video file
        namer: PlexFileNamer instance
        media_info: Media information from ffmpeg probe
    
    Returns:
        Tuple of (edition_info, combined_optional_info)
    """
    # Extract edition info separately
    edition_info = namer.extract_edition_info(file_path.name)
    
    # Extract and combine optional info
    filename_optional_info = namer.extract_optional_info(file_path.name)
    combined_optional_info = namer.combine_optional_info(filename_optional_info, media_info)
    
    if edition_info:
        print(f"Edition detected: {edition_info}")
    
    if combined_optional_info:
        print(f"Optional info: {combined_optional_info}")
        # Show if actual file data differs from filename claims
        check_resolution_mismatch(filename_optional_info, media_info)
    
    return edition_info, combined_optional_info


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


def process_video_file(file_path: str, api_key: Optional[str] = None, media_type: str = "auto", dry_run: bool = False, parentheses_only: bool = False, pattern: Optional[str] = None, root_folder: Optional[str] = None, show_name: Optional[str] = None) -> Optional[str]:
    """
    Main function to process a video file:
    1. Extract video duration
    2. Parse filename for title and year (or use custom pattern)
    3. Fetch metadata from TMDb
    4. Generate Plex-compliant filename
    
    Args:
        file_path: Path to the video file
        api_key: TMDb API key (or set TMDB_API_KEY env var)
        media_type: "movie", "tv", or "auto" (auto-detect)
        dry_run: If True, don't actually rename, just return the new path
        parentheses_only: If True, only look for years in parentheses format
        pattern: Custom pattern string for complex file structures
        root_folder: Root folder for pattern matching
    
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
        # This shouldn't happen if called from process_path, but handle it gracefully
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
    
    # Initialize variables to avoid "referenced before assignment" errors
    title = show_name if show_name else file_path.stem
    year = None
    season = None
    episode = None
    air_date = None
    is_date_based = False
    part_number = None
    
    # Use pattern matching if provided
    if pattern:
        print(f"Using custom pattern: {pattern}")
        if show_name:
            print(f"Using explicit show name: {show_name}")
        
        # If root_folder is not explicitly provided, use the parent directory of the file
        if root_folder:
            pattern_root = Path(root_folder)
        else:
            # Use the directory containing the file as root
            pattern_root = file_path.parent
            
        pattern_data = PatternMatcher.parse_pattern_file(file_path, pattern, pattern_root)
        
        if pattern_data:
            print("✓ Pattern matched successfully")
            # Priority for title/show name:
            # 1. Explicit show name (--show-name)
            # 2. Pattern-extracted show_name or title (if not marked as ignored)
            # 3. Filename as fallback
            
            if show_name:
                title = show_name
                print(f"Using explicit show name: {show_name}")
            elif pattern_data.get('show_name'):
                title = pattern_data['show_name']
                print(f"Using pattern-extracted show name: {title}")
            elif pattern_data.get('title'):
                title = pattern_data['title']
                print(f"Using pattern-extracted title: {title}")
            else:
                title = show_name if show_name else file_path.stem
                print(f"Using fallback title: {title}")
                
            # Show what was ignored
            if pattern_data.get('ignored_show_name'):
                print(f"Ignored show name from pattern: {pattern_data['ignored_show_name']}")
            if pattern_data.get('ignored_title'):
                print(f"Ignored title from pattern: {pattern_data['ignored_title']}")
            year = pattern_data.get('year')
            season = None
            episode = None
            air_date = pattern_data.get('air_date')
            is_date_based = pattern_data.get('is_date_based', False)
            is_tv_show = pattern_data.get('is_tv_show', False)
            part_number = pattern_data.get('part_number')
            
            print(f"Parsed title: {title}")
            if year:
                print(f"Parsed year: {year}")
            if air_date:
                print(f"Parsed air date: {air_date}")
                print(f"Date-based TV show: {is_date_based}")
            
            # Force TV type for date-based shows
            if is_date_based:
                media_type = "tv"
                print(f"Detected type: tv (date-based)")
        else:
            print("❌ Pattern did not match - falling back to standard parsing")
            # Reset pattern to trigger standard analysis
            pattern = None
    
    # Standard analysis if no pattern or pattern failed
    if not pattern:
        # Smart TV show analysis
        tv_analysis = namer.analyze_tv_show(file_path, parentheses_only)
        
        # Override show name if explicitly provided
        if show_name:
            print(f"Using explicit show name: {show_name}")
            title = show_name
        else:
            title = tv_analysis['show_name']
            
        print(f"Parsed title: {title}")
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
        
        # When explicit show name is provided, assume it's a TV show
        if show_name:
            media_type = "tv"
            print(f"Forcing type to TV since explicit show name provided")
        # Auto-detect media type if needed - TV analysis takes precedence
        elif media_type == "auto":
            media_type = "tv" if tv_analysis['is_tv_show'] else "movie"
            print(f"Detected type: {media_type}")
        elif media_type != "tv" and tv_analysis['is_tv_show']:
            # User forced movie/other type but we detected TV show - warn and override
            print(f"⚠️  WARNING: --type {media_type} specified but detected TV show with S{tv_analysis['season']:02d}E{tv_analysis['episode']:02d}")
            print(f"   Overriding to --type tv for proper TV show processing")
            media_type = "tv"
        
        # Extract individual values for compatibility
        year = tv_analysis['year']
        season = tv_analysis['season']
        episode = tv_analysis['episode']
        air_date = None
        is_date_based = False
        part_number = None
        
        # Check for part numbers in filename (PT1, PT2, Part 1, Part 2, etc.)
        if not part_number:
            part_patterns = [
                r'\.pt(\d+)',      # .PT1, .PT2 (lowercase for matching)
                r'\.part\s*(\d+)', # .Part1, .Part 2
                r'\.p(\d+)',       # .P1, .P2
                r'\spart\s*(\d+)', # Part 1, Part 2
                r'\spt(\d+)',      # PT1, PT2
            ]
            
            filename_lower = file_path.stem.lower()
            for pattern in part_patterns:
                part_match = re.search(pattern, filename_lower)
                if part_match:
                    part_number = int(part_match.group(1))
                    print(f"Extracted part number from filename: {part_number}")
                    break
        
        # Check for dates in filename even if not detected as date-based TV
        if not air_date and show_name:  # Only for explicit show names (likely date-based shows)
            # Try to extract date from filename using common patterns
            # Order matters - more specific patterns first
            date_patterns = [
                r'(\d{4})[-.](\d{1,2})[-.](\d{1,2})',  # YYYY-MM-DD (most specific, check first)
                r'(\d{1,2})[-.](\d{1,2})[-.](\d{4})',  # DD-MM-YYYY or DD.MM.YYYY
                r'\b(\d{1,2})[-.](\d{1,2})[-.](\d{2})\b',  # DD-MM-YY or DD.MM.YY (word boundary to avoid partial matches)
            ]
            
            filename_lower = file_path.stem.lower()
            for pattern in date_patterns:
                matches = re.findall(pattern, filename_lower)
                if matches:
                    # Take the first match
                    match = matches[0]
                    try:
                        if len(match[2]) == 2:  # DD-MM-YY format
                            day, month, year_short = match
                            year_full = f"20{year_short}" if int(year_short) < 50 else f"19{year_short}"
                            air_date = f"{year_full}-{month.zfill(2)}-{day.zfill(2)}"
                        elif len(match[0]) == 4:  # YYYY-MM-DD format
                            year_full, month, day = match
                            air_date = f"{year_full}-{month.zfill(2)}-{day.zfill(2)}"
                        else:  # DD-MM-YYYY format
                            day, month, year_full = match
                            air_date = f"{year_full}-{month.zfill(2)}-{day.zfill(2)}"
                        
                        # Validate date
                        from datetime import datetime
                        datetime.strptime(air_date, '%Y-%m-%d')
                        
                        print(f"Extracted air date from filename: {air_date}")
                        is_date_based = True
                        # Clear fake season/episode since we have a date
                        season = None
                        episode = None
                        break
                    except (ValueError, IndexError):
                        continue
    
    # Search for metadata
    print(f"\nSearching TMDb for: {title}")
    
    if media_type == "tv":
        # Search for TV show
        # For explicit show names (likely long-running shows), don't filter by year since
        # the year might be from a specific episode, not when the show started
        search_year = None if show_name else year
        show = tmdb.search_tv(title, search_year, duration_minutes)
        if show:
            print(f"Found TV show: {show['name']} ({show.get('first_air_date', 'N/A')[:4]})")
            
            # Get detailed show info
            details = tmdb.get_tv_details(show['id'])
            if details:
                show_year = int(details['first_air_date'][:4]) if details.get('first_air_date') else None
                
                # Get episode details for episode title
                episode_title = None
                
                # If we have an air date but no season/episode, try to find the episode by date
                if air_date and not (season and episode):
                    if part_number:
                        print(f"Searching for episode that aired on {air_date} (Part {part_number})...")
                    else:
                        print(f"Searching for episode that aired on {air_date}...")
                    episode_by_date = tmdb.find_episode_by_date(show['id'], air_date, part_number)
                    if episode_by_date:
                        season = episode_by_date['season_number']
                        episode = episode_by_date['episode_number']
                        episode_title = episode_by_date['episode_title']
                        print(f"Found episode by date: S{season:02d}E{episode:02d} - {episode_title}")
                    else:
                        print(f"No episode found for air date {air_date}")
                        # For date-based shows, skip files when no episode is found
                        if is_date_based:
                            print("Skipping file - no episode found for date-based show")
                            return None
                
                # Get episode details if we have season/episode
                if season and episode:
                    if not episode_title:  # Only fetch if we don't already have it from date lookup
                        episode_details = tmdb.get_episode_details(show['id'], int(season), int(episode))
                        if episode_details and episode_details.get('name'):
                            episode_title = episode_details['name']
                            print(f"Found episode title: {episode_title}")
                
                # Extract edition and optional info from filename and combine with media info
                edition_info, combined_optional_info = process_optional_info(file_path, namer, media_info)
                
                # Generate new filename
                if season and episode:
                    # Standard season/episode TV show (prefer this over date-based when available)
                    new_name = namer.format_tv_name(
                        details['name'],
                        int(season),
                        int(episode),
                        episode_title=episode_title,
                        year=show_year,
                        tmdb_id=show['id'],
                        optional_info=combined_optional_info
                    )
                elif is_date_based and air_date:
                    # Date-based TV show (only when no specific episode found)
                    new_name = namer.format_date_based_tv_name(
                        details['name'],
                        air_date,
                        episode_title=episode_title,
                        year=show_year,
                        tmdb_id=show['id'],
                        optional_info=combined_optional_info,
                        part_number=part_number
                    )
                else:
                    # Default to S01E01 if not detected
                    new_name = namer.format_tv_name(
                        details['name'],
                        1, 1,
                        year=show_year,
                        tmdb_id=show['id'],
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
        movie = tmdb.search_movie(title, year, duration_minutes)
        if movie:
            print(f"Found movie: {movie['title']} ({movie.get('release_date', 'N/A')[:4]})")
            
            # Get detailed movie info
            details = tmdb.get_movie_details(movie['id'])
            if details:
                movie_year = int(details['release_date'][:4]) if details.get('release_date') else year or 0
                
                # Extract edition and optional info from filename and combine with media info
                edition_info, combined_optional_info = process_optional_info(file_path, namer, media_info)
                
                # Generate new filename
                new_name = namer.format_movie_name(details['title'], movie_year, movie['id'], edition_info, combined_optional_info)
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
                 skip_confirmation: bool = False, pattern: Optional[str] = None, 
                 root_folder: Optional[str] = None, show_name: Optional[str] = None, 
                 skip_formatted: bool = False) -> None:
    """
    Process a file or directory of video files
    
    Args:
        path: File or directory path
        api_key: TMDb API key
        media_type: "movie", "tv", or "auto"
        dry_run: Preview mode without renaming
        rename: Actually rename files (ignored if dry_run is True)
        skip_confirmation: Skip confirmation prompt for each rename
        pattern: Custom pattern for matching complex file structures
        root_folder: Root folder path for pattern matching
        show_name: Explicitly specify the show name when it can't be extracted from folder structure
        skip_formatted: Skip files already properly formatted with TMDb IDs and backup files
    """
    # For non-rename modes, get files once and process
    if dry_run or not rename:
        video_files = get_video_files(path)
        if not video_files:
            print(f"No video files found in: {path}")
            return
        
        print(f"\nFound {len(video_files)} video file(s)")
        print("=" * 60)
        
        _process_file_list(video_files, api_key, media_type, dry_run, rename, parentheses_only, 
                          skip_confirmation, pattern, root_folder, show_name, skip_formatted)
    else:
        # For rename mode, use dynamic file discovery to handle path changes
        print(f"\nProcessing files in: {path}")
        print("=" * 60)
        
        _process_with_dynamic_discovery(path, api_key, media_type, dry_run, rename, parentheses_only, 
                                       skip_confirmation, pattern, root_folder, show_name, skip_formatted)


def _process_file_list(video_files: List[str], api_key: Optional[str], media_type: str, 
                      dry_run: bool, rename: bool, parentheses_only: bool,
                      skip_confirmation: bool, pattern: Optional[str], 
                      root_folder: Optional[str], show_name: Optional[str], 
                      skip_formatted: bool) -> None:
    """Process a fixed list of video files"""
    successful = 0
    failed = 0
    skipped = 0
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Processing: {video_file}")
        print("-" * 60)
        
        try:
            # Check if file still exists (important for network shares and long-running operations)
            if not Path(video_file).exists():
                print(f"⚠️  File no longer exists (may have been moved/renamed): {video_file}")
                skipped += 1
                continue
            
            # Check if file should be skipped
            if skip_formatted and PlexFileNamer.is_already_formatted(Path(video_file)):
                print("✓ File already properly formatted with TMDb ID and has backup file, skipping")
                skipped += 1
                continue
            
            new_path = process_video_file(str(video_file), api_key, media_type, dry_run, parentheses_only, pattern, root_folder, show_name)
            
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


def _process_with_dynamic_discovery(base_path: str, api_key: Optional[str], media_type: str, 
                                   dry_run: bool, rename: bool, parentheses_only: bool,
                                   skip_confirmation: bool, pattern: Optional[str], 
                                   root_folder: Optional[str], show_name: Optional[str], 
                                   skip_formatted: bool) -> None:
    """Process files with dynamic discovery to handle renamed files during processing"""
    successful = 0
    failed = 0
    skipped = 0
    processed_files = set()  # Track files we've already processed
    
    iteration = 0
    max_iterations = 10  # Safety limit to prevent infinite loops
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get current list of video files
        current_files = get_video_files(base_path)
        
        # Filter out files we've already processed (by tracking original paths)
        unprocessed_files = [f for f in current_files if f not in processed_files]
        
        if not unprocessed_files:
            break
            
        print(f"\nIteration {iteration}: Found {len(unprocessed_files)} unprocessed files")
        
        files_processed_this_iteration = 0
        
        for video_file in unprocessed_files:
            # Mark as processed before attempting to process (to avoid reprocessing if renamed)
            processed_files.add(video_file)
            files_processed_this_iteration += 1
            
            print(f"\n[{successful + failed + skipped + 1}] Processing: {video_file}")
            print("-" * 60)
            
            try:
                # Check if file still exists
                if not Path(video_file).exists():
                    print(f"⚠️  File no longer exists (may have been moved/renamed): {video_file}")
                    skipped += 1
                    continue
                
                # Check if file should be skipped
                if skip_formatted and PlexFileNamer.is_already_formatted(Path(video_file)):
                    print("✓ File already properly formatted with TMDb ID and has backup file, skipping")
                    skipped += 1
                    continue
                
                new_path = process_video_file(str(video_file), api_key, media_type, dry_run, parentheses_only, pattern, root_folder, show_name)
                
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
                                    
                                    # Add the new path to processed files to avoid reprocessing
                                    processed_files.add(str(new_path))
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
        
        # If we didn't process any files this iteration, we're done
        if files_processed_this_iteration == 0:
            break
    
    # Summary
    total_processed = successful + failed + skipped
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {total_processed}")
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
    parser.add_argument("--pattern", 
                       help="Custom pattern for matching complex file structures (e.g., 'SHOW_NAME/DATE_FORMAT{YYYY-MM-DD}/IGNORE')")
    parser.add_argument("--root-folder", 
                       help="Root folder path for pattern matching (used with --pattern)")
    parser.add_argument("--show-name", 
                       help="Explicitly specify the show name when it can't be extracted from folder structure")
    parser.add_argument("--skip-formatted", action="store_true",
                       help="Skip files that are already properly formatted with TMDb IDs and have backup files")
    
    args = parser.parse_args()
    
    # Handle revert mode
    if args.revert:
        revert_renames(args.path, args.dry_run)
    else:
        # Process the path (file or directory)
        process_path(args.path, args.api_key, args.type, args.dry_run, args.rename, args.parentheses_only,
                    args.skip_confirmation, args.pattern, args.root_folder, args.show_name, args.skip_formatted)


if __name__ == "__main__":
    main()
    