from pytube import YouTube
from pytube import Playlist
import sys


playlist_url = sys.argv[1]
video_dir = '.'

playlist = Playlist(playlist_url)
print(f'Downloading playlist: {playlist.title}')
for video in playlist.videos:
    print(f'Downloading: {video.title}')

    audio_streams = video.streams.filter(adaptive=True, abr="160kbps", mime_type="audio/webm")    
    video_streams = video.streams.filter(adaptive=True, res="720p", mime_type="video/mp4")

    if not (Path(video_dir) / f'{video.title}.webm').exists():
        print('\tAudio:')
        audio_streams[0].download(video_dir)
        print('\tVideo:')    
        video_streams[0].download()
    else:
        print('\t Exists, continuing')


    # print(f'Downloading video: {video.title} {len(video_streams)} {len(audio_streams)}')
    # print('\n'.join(str(s) for s in video.streams))    
    # if len(video_streams) != 1 or len(audio_streams) != 1:
    #     print('  ' + '\n  '.join(str(s) for s in video.streams))
    #     print()
    
    


