import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="YouTube Analiz", layout="wide")

st.title("📊 YouTube Kanal Analiz Dashboard'u")
st.markdown("Bu panel sayesinde istediğiniz YouTube kanalının son videolarını çekip inceleyebilirsiniz.")

# Yan menü (API Anahtarı buraya girilecek, böylece şifreniz kodun içinde açıkta kalmayacak)
st.sidebar.header("Ayarlar")
api_key = st.sidebar.text_input("YouTube API Anahtarınız:", type="password")
handle = st.sidebar.text_input("Kanalın Kullanıcı Adı (Örn: NevsinMenguTV):")

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
            
            if not response['items']:
                st.error("Kanal bulunamadı. Lütfen kullanıcı adını kontrol edin.")
            else:
                channel_id = response['items'][0]['snippet']['channelId']
                channel_name = response['items'][0]['snippet']['title']
                
                # 2. Kanalın "Yüklemeler" oynatma listesini bul
                ch_request = youtube.channels().list(part="contentDetails", id=channel_id)
                ch_response = ch_request.execute()
                uploads_id = ch_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                # 3. Son 50 videoyu çek
                pl_request = youtube.playlistItems().list(part="contentDetails", playlistId=uploads_id, maxResults=50)
                pl_response = pl_request.execute()
                
                video_ids = [item['contentDetails']['videoId'] for item in pl_response['items']]
                
                # 4. Videoların izlenme istatistiklerini al
                vid_request = youtube.videos().list(part="snippet,statistics", id=','.join(video_ids))
                vid_response = vid_request.execute()
                
                videos_data = []
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
                st.success(f"✅ {channel_name} kanalına ait son {len(df)} videonun verisi başarıyla çekildi!")
                
                # Metrikler
                col1, col2, col3 = st.columns(3)
                col1.metric("Ortalama İzlenme", f"{int(df['İzlenme'].mean()):,}")
                col2.metric("Toplam İzlenme", f"{df['İzlenme'].sum():,}")
                col3.metric("Ortalama Beğeni", f"{int(df['Beğeni'].mean()):,}")
                
                st.subheader("📈 İzlenme Trendi")
                fig = px.line(df, x="Yayın Tarihi", y="İzlenme", title="Son Videoların İzlenme Grafiği", markers=True)
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 Detaylı Veri Tablosu")
                st.dataframe(df)
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
