import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="YouTube Analiz", layout="wide")

st.title("📊 YouTube Kanal Analiz Dashboard'u")
st.markdown("Bu panel sayesinde istediğiniz YouTube kanalının videolarını çekip inceleyebilirsiniz.")

st.sidebar.header("Ayarlar")
api_key = st.sidebar.text_input("YouTube API Anahtarınız:", type="password")
handle = st.sidebar.text_input("Kanalın Kullanıcı Adı (Örn: NevsinMenguTV):")

# Yeni Eklenen Filtreleme Bölümü
st.sidebar.subheader("Filtreleme Seçenekleri")
filter_type = st.sidebar.radio("Nasıl veri çekmek istersiniz?", ["Son X Video", "Belirli Bir Tarihten İtibaren"])

if filter_type == "Son X Video":
    max_videos = st.sidebar.number_input("Çekilecek Video Sayısı (Maks 200):", min_value=1, max_value=200, value=100)
else:
    # Varsayılan tarihi 01.01.2026 yaptık
    start_date = st.sidebar.date_input("Başlangıç Tarihi:", value=pd.to_datetime("2026-01-01"))

if st.sidebar.button("Verileri Çek ve Analiz Et"):
    if not api_key or not handle:
        st.warning("Lütfen API Anahtarınızı ve Kanal Kullanıcı Adını girin.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # 1. Kullanıcı adından Kanal ID'sini bul
            if handle.startswith('@'):
                handle = handle[1:]
                
            request = youtube.search().list(part="snippet", q=handle, type="channel", maxResults=1)
            response = request.execute()
            
            if not response.get('items'):
                st.error("Kanal bulunamadı. Lütfen kullanıcı adını kontrol edin.")
            else:
                channel_id = response['items'][0]['snippet']['channelId']
                channel_name = response['items'][0]['snippet']['title']
                
                # 2. Kanalın "Yüklemeler" oynatma listesini bul
                ch_request = youtube.channels().list(part="contentDetails", id=channel_id)
                ch_response = ch_request.execute()
                uploads_id = ch_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                # 3. Videoları Çekme (Sayfalama - Pagination ile)
                video_ids = []
                next_page_token = None
                keep_fetching = True
                
                with st.spinner("Videolar taranıyor, lütfen bekleyin..."):
                    while keep_fetching:
                        pl_request = youtube.playlistItems().list(
                            part="snippet,contentDetails", 
                            playlistId=uploads_id, 
                            maxResults=50,
                            pageToken=next_page_token
                        )
                        pl_response = pl_request.execute()
                        
                        for item in pl_response['items']:
                            pub_date_str = item['snippet']['publishedAt']
                            pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d").date()
                            
                            # Tarih filtresi kontrolü
                            if filter_type == "Belirli Bir Tarihten İtibaren":
                                if pub_date < start_date:
                                    keep_fetching = False # Belirlenen tarihten eskiye geldik, dur!
                                    break
                                video_ids.append(item['contentDetails']['videoId'])
                            
                            # Sayı filtresi kontrolü
                            else:
                                if len(video_ids) >= max_videos:
                                    keep_fetching = False # İstenen sayıya ulaştık, dur!
                                    break
                                video_ids.append(item['contentDetails']['videoId'])
                                
                        next_page_token = pl_response.get('nextPageToken')
                        if not next_page_token:
                            break # Kanalda başka video kalmadıysa dur
                
                if not video_ids:
                    st.warning("Bu kriterlere uygun video bulunamadı.")
                else:
                    # 4. Videoların detaylı istatistiklerini 50'şerli gruplar halinde al (API sınırı)
                    videos_data = []
                    for i in range(0, len(video_ids), 50):
                        chunk = video_ids[i:i+50]
                        vid_request = youtube.videos().list(part="snippet,statistics", id=','.join(chunk))
                        vid_response = vid_request.execute()
                        
                        for item in vid_response['items']:
                            videos_data.append({
                                "Başlık": item['snippet']['title'],
                                "Yayın Tarihi": item['snippet']['publishedAt'][:10],
                                "İzlenme": int(item['statistics'].get('viewCount', 0)),
                                "Beğeni": int(item['statistics'].get('likeCount', 0)),
                                "Yorum": int(item['statistics'].get('commentCount', 0))
                            })
                    
                    df = pd.DataFrame(videos_data)
                    
                    # Sonuçları Göster
                    st.success(f"✅ {channel_name} kanalına ait {len(df)} videonun verisi başarıyla çekildi!")
                    
                    # Metrikler
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Ortalama İzlenme", f"{int(df['İzlenme'].mean()):,}")
                    col2.metric("Toplam İzlenme", f"{df['İzlenme'].sum():,}")
                    col3.metric("Ortalama Beğeni", f"{int(df['Beğeni'].mean()):,}")
                    
                    st.subheader("📈 İzlenme Trendi")
                    fig = px.line(df, x="Yayın Tarihi", y="İzlenme", title="İzlenme Grafiği", markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("📋 Detaylı Veri Tablosu")
                    st.dataframe(df)
                    
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
