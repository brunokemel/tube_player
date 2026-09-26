import yt_dlp
import vlc
import time
import os
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
    #caminho pasta VLC
    vlc_path = os.path.join(os.getcwd(), "vlc", "plugins")
    instance = vlc.Instance("--plugin-path=" + vlc_path)
    player = instance.media_player_new()
    media = instance.media_new(url_stream)
    player.set_media(media)
    player.play()
    print("Tocando")
    while True:
        state = player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error):
            break
        time.sleep(1)

# Caso queira testar o código, descomente as linhas abaixo e coloque um link de vídeo do YouTube
# youtube_url = input("Coloque seu link aqui: ")
# stream_url = obter_url_audio(youtube_url)
# tocar_stream(stream_url)