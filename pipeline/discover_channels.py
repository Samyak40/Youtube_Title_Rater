import json
import logging
from . import config
from . import youtube_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def determine_size_tier(subscribers: int) -> str:
    if subscribers < 50_000:
        return "micro"
    elif subscribers < 250_000:
        return "small"
    elif subscribers < 1_000_000:
        return "mid"
    elif subscribers <= 3_000_000:
        return "large"
    else:
        return "outlier"

def run_discovery():
    discovered_channels = {}  # channel_id -> channel_data
    
    for niche, keywords in config.NICHE_KEYWORDS.items():
        logging.info(f"Discovering channels for niche: {niche}")
        for keyword in keywords:
            logging.info(f"  Searching keyword: '{keyword}'")
            try:
                channels = youtube_client.search_channels(keyword, config.CHANNELS_PER_KEYWORD)
                
                # Fetch stats for this batch
                channel_ids = [c["channel_id"] for c in channels]
                if not channel_ids:
                    continue
                    
                stats_list = youtube_client.get_channel_stats(channel_ids)
                stats_map = {item["id"]: item["statistics"] for item in stats_list}
                
                for channel in channels:
                    cid = channel["channel_id"]
                    stats = stats_map.get(cid, {})
                    
                    sub_count_str = stats.get("subscriberCount", "0")
                    sub_count = int(sub_count_str) if sub_count_str.isdigit() else 0
                    
                    video_count_str = stats.get("videoCount", "0")
                    video_count = int(video_count_str) if video_count_str.isdigit() else 0
                    
                    view_count_str = stats.get("viewCount", "0")
                    view_count = int(view_count_str) if view_count_str.isdigit() else 0
                    
                    # Apply filter but keep outliers
                    if sub_count < config.MIN_SUBSCRIBERS:
                        continue
                        
                    size_tier = determine_size_tier(sub_count)
                    
                    if cid in discovered_channels:
                        if keyword not in discovered_channels[cid]["niche_tags"]:
                            discovered_channels[cid]["niche_tags"].append(keyword)
                    else:
                        discovered_channels[cid] = {
                            "channel_id": cid,
                            "channel_title": channel["channel_title"],
                            "subscriber_count": sub_count,
                            "video_count": video_count,
                            "total_view_count": view_count,
                            "size_tier": size_tier,
                            "niche_tags": [keyword]
                        }
            except Exception as e:
                logging.error(f"Error during discovery for keyword '{keyword}': {e}")
                
    # Save to JSON
    output_file = config.OUTPUT_DIR / "discovered_channels.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(list(discovered_channels.values()), f, indent=2, ensure_ascii=False)
        
    # Print Summary
    print("\n--- Discovery Summary ---")
    print(f"Total Unique Channels Found: {len(discovered_channels)}")
    
    size_breakdown = {}
    niche_breakdown = {}
    
    for c in discovered_channels.values():
        size = c["size_tier"]
        size_breakdown[size] = size_breakdown.get(size, 0) + 1
        
        for tag in c["niche_tags"]:
            niche_breakdown[tag] = niche_breakdown.get(tag, 0) + 1
            
    print("\nSize Tier Breakdown:")
    for size, count in size_breakdown.items():
        print(f"  {size}: {count}")
        
    print("\nNiche/Keyword Breakdown (overlaps possible):")
    for niche, count in niche_breakdown.items():
        print(f"  {niche}: {count}")

if __name__ == "__main__":
    run_discovery()
