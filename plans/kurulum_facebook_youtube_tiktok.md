# Facebook, YouTube ve TikTok kurulumu

Programın üç platform için kodu hazır ve test edildi. Gizlilik ve kullanım şartları sayfaları yayında:
- https://asiyeozsoy.github.io/social-autopilot/legal/privacy.html
- https://asiyeozsoy.github.io/social-autopilot/legal/terms.html

Anahtar/kodları her zaman **sadece GitHub → Settings → Secrets**'a siz yapıştırın, sohbete yazmayın.

## 1. Facebook (~5 dk)
1. Business Suite → Factyeap portföyü → Sistem kullanıcıları → **Autopilot Publisher** → **Jeton oluştur**
   - Uygulama: Social Autopilot · Süre: Asla
   - İzinler: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`
2. Kodu GitHub'a **yeni secret** olarak ekleyin: `META_SYSTEM_TOKEN`
3. TinyNotes için önce bir Facebook sayfası gerekiyor (şu an yok). İsterseniz açarız; sonra portföye ve sistem kullanıcısına ekleriz.

## 2. YouTube (~15 dk, iki kanal için)
Ön koşul: Factyeap ve TinyNotes'un YouTube kanalları açık olmalı.
1. console.cloud.google.com → yeni proje **Social Autopilot**
2. **YouTube Data API v3** → Etkinleştir
3. **OAuth izin ekranı**: External · uygulama adı Social Autopilot · gizlilik ve şartlar bağlantıları yukarıdaki sayfalar · **Yayınla (In production)**
4. **Kimlik bilgileri → OAuth istemci kimliği → Web uygulaması** · yönlendirme adresi: `https://developers.google.com/oauthplayground`
5. İstemci kimliği ve gizli anahtarı GitHub'a: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`
6. developers.google.com/oauthplayground → ⚙️ → "Use your own OAuth credentials" → kapsam `https://www.googleapis.com/auth/youtube.upload` → Authorize → **TinyNotes kanalını** seçin → "Exchange authorization code" → **Refresh token** → GitHub: `TINYNOTES_YT_REFRESH_TOKEN`
7. 6. adımı Factyeap kanalıyla tekrarlayın → `FACTYEAP_YT_REFRESH_TOKEN`

Not: Google, onaylanmamış uygulama için "Google bu uygulamayı doğrulamadı" uyarısı gösterir; kendi uygulamanız olduğu için **Gelişmiş → devam et** deyin. Günde ~6 video yükleme kotası var.

## 3. TikTok (başvuru ~10 dk, onay günler/haftalar)
1. developers.tiktok.com → TikTok hesabınızla giriş → **Manage apps → Connect an app**
2. Uygulama bilgileri: ad Social Autopilot · web sitesi `https://asiyeozsoy.github.io/social-autopilot` · şartlar ve gizlilik bağlantıları yukarıda
3. Ürünler: **Login Kit** + **Content Posting API** (Direct Post açık) · kapsamlar `user.info.basic`, `video.publish`
4. **URL properties**: TikTok'un verdiği doğrulama dosyasını Claude GitHub Pages'e koyar
5. **Submit for review**. Onaylanana kadar TikTok'a giden postlar "yalnızca ben" görünür.
