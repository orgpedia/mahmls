from pytube import YouTube
from pytube import Playlist
import sys
from pathlib import Path

playlist_urls = {'Monsoon-2023': 'https://www.youtube.com/playlist?list=PLIJyj1g6Ss2q6PcPMoDHIq_bFyEI5a0lo',
                 'Budget-2023': 'https://www.youtube.com/playlist?list=PLIJyj1g6Ss2oqu32OiRoQllWdcBH7NMyR',
                 'Winter-2022': 'https://www.youtube.com/playlist?list=PLIJyj1g6Ss2pzAQF7FtxTbcbxy_45174H'
                 }

video_dir = Path('.')

for (dir_name, playlist_url) in playlist_urls.items():
    playlist = Playlist(playlist_url)
    print(f'Downloading playlist: {playlist.title}')
    for video in playlist.videos:
        print(f'Downloading: {video.title}')
        
        video_streams = video.streams.filter(adaptive=True, res="144p", mime_type="video/mp4")
        assert len(video_streams) == 1
        
        if not (video_dir / Path(dir_name) / f'{video.title}.mp4').exists():
            video_streams[0].download(video_dir / Path(dir_name))
        else:
            print('\t Exists, continuing')
    break
