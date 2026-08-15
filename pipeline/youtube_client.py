import time
import logging
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .config import API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for retries
MAX_RETRIES = 3
INITIAL_BACKOFF = 2

def get_youtube_service():
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set in environment variables.")
    return build('youtube', 'v3', developerKey=API_KEY)

def _execute_with_retry(request) -> dict:
    retries = 0
    backoff = INITIAL_BACKOFF
    while True:
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status in [403, 429, 500, 503] and retries < MAX_RETRIES:
                logger.warning(f"API error {e.resp.status}: {e.reason}. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                retries += 1
                backoff *= 2
            else:
                logger.error(f"Failed after {retries} retries or non-retriable error: {e}")
                raise e

def search_channels(keyword: str, max_results: int = 30) -> List[Dict]:
    youtube = get_youtube_service()
    channels = []
    next_page_token = None
    
    while len(channels) < max_results:
        remaining = max_results - len(channels)
        limit = min(50, remaining)
        
        request = youtube.search().list(
            part="snippet",
            q=keyword,
            type="channel",
            maxResults=limit,
            pageToken=next_page_token
        )
        
        response = _execute_with_retry(request)
        for item in response.get("items", []):
            channels.append({
                "channel_id": item["snippet"]["channelId"],
                "channel_title": item["snippet"]["title"]
            })
            
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
            
    return channels[:max_results]

def get_channel_stats(channel_ids: List[str]) -> List[Dict]:
    youtube = get_youtube_service()
    stats = []
    
    # Batch up to 50
    for i in range(0, len(channel_ids), 50):
        batch_ids = channel_ids[i:i+50]
        request = youtube.channels().list(
            part="statistics",
            id=",".join(batch_ids)
        )
        
        response = _execute_with_retry(request)
        for item in response.get("items", []):
            stats.append(item)
            
    return stats

def get_uploads_playlist_id(channel_id: str) -> Optional[str]:
    youtube = get_youtube_service()
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = _execute_with_retry(request)
    
    items = response.get("items", [])
    if items:
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return None

def get_playlist_video_ids(playlist_id: str, max_videos: int = 100) -> List[str]:
    youtube = get_youtube_service()
    video_ids = []
    next_page_token = None
    
    while len(video_ids) < max_videos:
        remaining = max_videos - len(video_ids)
        limit = min(50, remaining)
        
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=limit,
            pageToken=next_page_token
        )
        
        response = _execute_with_retry(request)
        for item in response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
            
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
            
    return video_ids[:max_videos]

def get_video_stats(video_ids: List[str]) -> List[Dict]:
    youtube = get_youtube_service()
    stats = []
    
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i+50]
        request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(batch_ids)
        )
        
        response = _execute_with_retry(request)
        for item in response.get("items", []):
            stats.append(item)
            
    return stats
