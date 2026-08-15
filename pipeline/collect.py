import json
import csv
import logging
from datetime import datetime
from . import config
from . import youtube_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_discovered_channels():
    input_file = config.OUTPUT_DIR / "discovered_channels.json"
    if not input_file.exists():
        logging.error(f"Input file {input_file} not found. Run discover_channels.py first.")
        return []
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_collection():
    channels = load_discovered_channels()
    if not channels:
        return

    # Group channels by their primary niche for separate CSVs
    niche_groups = {}
    for c in channels:
        primary_niche = "mixed"
        for main_niche, keywords in config.NICHE_KEYWORDS.items():
            if any(tag in keywords for tag in c["niche_tags"]):
                primary_niche = main_niche
                break
        
        if primary_niche not in niche_groups:
            niche_groups[primary_niche] = []
        niche_groups[primary_niche].append(c)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for niche, group in niche_groups.items():
        output_file = config.OUTPUT_DIR / f"{niche}_{timestamp}.csv"
        logging.info(f"Starting collection for niche: {niche}. Output: {output_file.name}")
        
        file_exists = output_file.exists()
        collected_video_ids = set()
        
        if file_exists:
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        collected_video_ids.add(row["video_id"])
            except Exception:
                pass
                
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = [
                "video_id", "title", "channel_id", "channel_title", 
                "subscriber_count", "view_count", "like_count", "published_at", 
                "category_id", "size_tier", "niche_tags"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            for i, channel in enumerate(group, 1):
                channel_id = channel["channel_id"]
                logging.info(f"Channel {i}/{len(group)}: {channel['channel_title']} ({channel_id})")
                
                try:
                    playlist_id = youtube_client.get_uploads_playlist_id(channel_id)
                    if not playlist_id:
                        logging.warning(f"  No uploads playlist found for {channel_id}")
                        continue
                        
                    video_ids = youtube_client.get_playlist_video_ids(playlist_id, config.MAX_VIDEOS_PER_CHANNEL)
                    new_video_ids = [vid for vid in video_ids if vid not in collected_video_ids]
                    
                    if not new_video_ids:
                        logging.info(f"  No new videos to fetch. Fetched 0/{len(video_ids)}.")
                        continue
                        
                    stats = youtube_client.get_video_stats(new_video_ids)
                    
                    written_count = 0
                    for stat in stats:
                        vid = stat["id"]
                        if vid in collected_video_ids:
                            continue
                            
                        snippet = stat.get("snippet", {})
                        statistics = stat.get("statistics", {})
                        
                        # Note: subscriber_count is the channel's current count at discovery time,
                        # not at the time the video was published. This is a known limitation.
                        writer.writerow({
                            "video_id": vid,
                            "title": snippet.get("title", ""),
                            "channel_id": channel_id,
                            "channel_title": channel["channel_title"],
                            "subscriber_count": channel["subscriber_count"],
                            "view_count": statistics.get("viewCount", "0"),
                            "like_count": statistics.get("likeCount", "0"),
                            "published_at": snippet.get("publishedAt", ""),
                            "category_id": snippet.get("categoryId", ""),
                            "size_tier": channel["size_tier"],
                            "niche_tags": json.dumps(channel["niche_tags"])
                        })
                        collected_video_ids.add(vid)
                        written_count += 1
                        
                    f.flush()
                    logging.info(f"  Fetched {written_count}/{len(video_ids)} videos.")
                    
                except Exception as e:
                    logging.error(f"  Failed processing channel {channel_id}: {e}")

if __name__ == "__main__":
    run_collection()
