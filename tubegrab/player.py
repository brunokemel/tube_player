import yt_dlp
import vlc
# funcao para obter a URL do stream de áudio do vídeo do YouTube
def obter_url_audio(youtube_url: str) -> str:
    ydl_opts = {
        'format' : 'bestaudio/best',
        'quiet' : True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        return info_dict.get('url')

def tocar_stream(url_stream: str) -> str:
    player = vlc.MediaPlayer(url_stream)
    player.play()
    print("Tocando")
    while True:
        pass

youtube_url = input("Coloque seu link aqui: ")
stream_url = obter_url_audio(youtube_url)
tocar_stream(stream_url)