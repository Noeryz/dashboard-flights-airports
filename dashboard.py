import html
import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Ketepatan Waktu Penerbangan AS",
                   page_icon="logo.png", layout="wide")

# Deteksi tema aktif Streamlit (dark/light) langsung dari server-side,
# supaya CSS & warna chart otomatis menyesuaikan tanpa menebak-nebak selector.
try:
    TEMA = st.context.theme.type  # "light" atau "dark"
except Exception:
    TEMA = "light"
GELAP = TEMA == "dark"

# =====================================================================
# KONSTANTA & SISTEM WARNA SEMANTIK
# =====================================================================
FILE_DATA = "Data_Dashboard_Final.parquet"
FILE_KOORDINAT = "airports_coords.csv"
URUTAN_BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
MIN_PENERBANGAN = 30

HIJAU_TUA, HIJAU, HIJAU_MUDA = "#0B5D3B", "#1B8A5A", "#74C69D"
PALET = [HIJAU_TUA, HIJAU_MUDA, HIJAU, "#B7E4C7", "#40916C", "#95D5B2", "#2D6A4F", "#D8F3DC"]

# Delay = makin tinggi makin parah -> skala "bahaya" krem ke merah tegas.
SKALA_DELAY = ["#FFF7ED", "#FFD8A8", "#FF9E57", "#E8552A", "#A3240C"]
# Volume/kepadatan = makin tinggi makin ramai -> skala amber (beda kesan dari "bahaya").
SKALA_VOLUME = ["#FFFBEA", "#FFE49A", "#FFBD5E", "#F2920B", "#B86B00"]
MERAH_BAHAYA, HIJAU_AMAN = "#E8552A", "#1B8A5A"
GAYA_PETA = "carto-darkmatter" if GELAP else "open-street-map"
RADIUS_PETA = 24 if GELAP else 18

WARNA_PENYEBAB = {
    'Maskapai': HIJAU_TUA,
    'Cuaca': "#2D81C4",
    'Sistem Navigasi Udara (NAS)': "#F2920B",
    'Keamanan': "#A3240C",
    'Pesawat Datang Terlambat': "#74C69D",
}


def warna_kpi(kolom, nilai):
    """Hijau = aman, kuning = sedang, merah = rawan. Dipakai di kartu KPI delay."""
    if pd.isna(nilai):
        return "#6FE3A3" if GELAP else "#0B5D3B"
    if kolom == 'delay_rate':
        return MERAH_BAHAYA if nilai >= 25 else ("#F2920B" if nilai >= 15 else HIJAU_AMAN)
    if kolom == 'avg_delay':
        return MERAH_BAHAYA if nilai >= 15 else ("#F2920B" if nilai >= 8 else HIJAU_AMAN)
    return "#6FE3A3" if GELAP else "#0B5D3B"

px.defaults.template = "plotly_dark" if GELAP else "plotly_white"
px.defaults.color_discrete_sequence = PALET
px.defaults.color_continuous_scale = SKALA_VOLUME

NAMA_MASKAPAI = {
    '9E': 'Endeavor Air', 'AA': 'American Airlines', 'AS': 'Alaska Airlines',
    'B6': 'JetBlue', 'DL': 'Delta Air Lines', 'F9': 'Frontier Airlines',
    'G4': 'Allegiant Air', 'HA': 'Hawaiian Airlines', 'MQ': 'Envoy Air',
    'NK': 'Spirit Airlines', 'OH': 'PSA Airlines', 'OO': 'SkyWest Airlines',
    'UA': 'United Airlines', 'WN': 'Southwest Airlines', 'YX': 'Republic Airways',
}
LABEL_PENYEBAB = {
    'total_carrier_delay': 'Maskapai',
    'total_weather_delay': 'Cuaca',
    'total_nas_delay': 'Sistem Navigasi Udara (NAS)',
    'total_security_delay': 'Keamanan',
    'total_late_aircraft_delay': 'Pesawat Datang Terlambat',
}
METRIK = {
    "Persentase delay (>15 menit)": ("delay_rate", "Penerbangan delay (%)"),
    "Rata-rata delay (menit)": ("avg_delay", "Rata-rata delay (menit)"),
}
KOLOM_WAJIB = [
    'ORIGIN', 'DEST', 'YEAR', 'MONTH', 'OP_UNIQUE_CARRIER',
    'avg_arr_delay', 'total_flights', 'delayed_flights',
    'total_carrier_delay', 'total_weather_delay', 'total_nas_delay',
    'total_security_delay', 'total_late_aircraft_delay',
    'origin_city', 'dest_city', 'total_passengers', 'total_seats',
]

try:
    _versi = tuple(int(x) for x in st.__version__.split('.')[:2])
except Exception:
    _versi = (0, 0)
LEBAR_PENUH = {"width": "stretch"} if _versi >= (1, 50) else {"use_container_width": True}

# Warna yang beda antara tema terang & gelap (sisanya -- sidebar duotone, hero -- sengaja dibuat sama di kedua tema sebagai identitas brand)
_BG = "#0A100C" if GELAP else "#FAF9F5"
_BLOB = "rgba(116,198,157,.16)" if GELAP else "rgba(116,198,157,.12)"
_PANEL = "#121B16" if GELAP else "#FFFFFF"
_PANEL_BORDER = "rgba(116,198,157,.18)" if GELAP else "rgba(11,93,59,.08)"
_TEKS_JUDUL = "#DFF4E8" if GELAP else "#0B5D3B"
_TEKS_LABEL = "#9FC9AF" if GELAP else "#3D6B57"
_TEKS_NILAI = "#6FE3A3" if GELAP else "#0B5D3B"
_INSIGHT_BG = "#12271C" if GELAP else "#E4F4EA"
_INSIGHT_TEKS = "#DDF2E4" if GELAP else "#12372A"

CSS_HALAMAN = f"""
.hero{{background:linear-gradient(120deg,#0B5D3B,#1B8A5A 60%,#52B788);color:#fff;padding:26px 32px 38px;
 border-radius:16px;position:relative;overflow:hidden;margin-bottom:18px;animation:fade .5s ease both}}
.hero h1{{margin:0;font-size:2rem;color:#fff;padding:0;position:relative;z-index:2}}
.hero p{{margin:6px 0 0;opacity:.92;color:#fff;position:relative;z-index:2}}
.pesawat{{position:absolute;bottom:8px;top:auto;left:-60px;font-size:20px;animation:terbang 10s linear infinite;opacity:.65;z-index:1}}
@keyframes terbang{{0%{{left:-60px;transform:translateY(0)}}50%{{transform:translateY(14px)}}100%{{left:105%;transform:translateY(0)}}}}
@keyframes fade{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.insight{{background:{_INSIGHT_BG};border-left:6px solid #1B8A5A;border-radius:10px;padding:14px 18px;margin:8px 0 22px;
 color:{_INSIGHT_TEKS};animation:fade .5s ease both;line-height:1.55}}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{{animation:fade .5s ease both}}
h2,h3{{color:{_TEKS_JUDUL}}}

/* ====== Legenda skala warna (strip gradient kecil) ====== */
.legenda{{display:flex;align-items:center;gap:10px;margin:4px 0 18px;font-size:13px;color:{_TEKS_LABEL}}}
.legenda .strip{{flex:0 0 140px;height:10px;border-radius:6px}}

/* ====== Badge sinyal delay (merah=rawan, hijau=aman) ====== */
.badge-bahaya{{background:rgba(232,85,42,.15);color:#E8552A;border:1px solid rgba(232,85,42,.35);
 border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}}
.badge-aman{{background:rgba(27,138,90,.15);color:{'#6FE3A3' if GELAP else '#1B8A5A'};border:1px solid rgba(27,138,90,.35);
 border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}}

/* ====== KONTEN UTAMA: aksen gradient tipis cuma di pojok, area baca tetap bersih ====== */
[data-testid="stAppViewContainer"]{{
  background-color:{_BG};
  background-image:
    radial-gradient(circle at 10% 8%, {_BLOB} 0%, transparent 30%),
    radial-gradient(circle at 92% 6%, {_BLOB} 0%, transparent 32%),
    radial-gradient(circle at 88% 92%, {_BLOB} 0%, transparent 30%),
    radial-gradient(circle at 6% 92%, {_BLOB} 0%, transparent 32%);
  border-radius:20px;margin:10px 12px 10px 0}}

/* ====== SIDEBAR: panel gelap duotone + tekstur noise halus (sama di kedua tema, identitas brand) ====== */
[data-testid="stSidebar"]{{
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0px, rgba(255,255,255,.035) 1px, transparent 1px, transparent 3px),
    repeating-linear-gradient(90deg, rgba(255,255,255,.035) 0px, rgba(255,255,255,.035) 1px, transparent 1px, transparent 3px),
    radial-gradient(circle at 20% 8%, rgba(116,198,157,.22) 0%, transparent 50%),
    radial-gradient(circle at 85% 92%, rgba(45,106,79,.30) 0%, transparent 55%),
    linear-gradient(165deg, #0B5D3B 0%, #073623 45%, #041912 100%);
  border-right:1px solid rgba(116,198,157,.18);
  box-shadow:8px 0 30px rgba(0,0,0,.35)}}
[data-testid="stSidebar"] *{{color:#E8F6EE !important}}
[data-testid="stSidebar"] hr{{border-color:rgba(232,246,238,.22) !important}}
[data-testid="stSidebar"] svg{{fill:#E8F6EE !important}}
[data-testid="stHeader"]{{background:transparent}}
[data-testid="stHeader"] svg{{fill:{_TEKS_LABEL} !important}}
"""

CSS_KARTU = f"""
body{{margin:0;font-family:"Source Sans Pro",Arial,sans-serif}}
.row{{display:flex;gap:14px}}
.k{{flex:1;background:{_PANEL};border-left:6px solid #1B8A5A;border-radius:12px;padding:14px 16px;
 box-shadow:0 2px 8px rgba(11,93,59,.15);border:1px solid {_PANEL_BORDER};border-left:6px solid #1B8A5A;
 transition:transform .22s,box-shadow .22s;animation:naik .5s ease both}}
.k:hover{{transform:translateY(-6px);box-shadow:0 12px 26px rgba(27,138,90,.30)}}
.t{{font-size:13px;color:{_TEKS_LABEL}}}
.v{{font-size:28px;font-weight:700;color:{_TEKS_NILAI};margin-top:4px}}
@keyframes naik{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
"""

JS_HITUNG = """
document.querySelectorAll('.n').forEach(function(el){
  var target=parseFloat(el.dataset.v), d=parseInt(el.dataset.d), t0=performance.now(), dur=1200;
  function fmt(v){return v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
  function step(t){var p=Math.min((t-t0)/dur,1), e=1-Math.pow(1-p,3);
    el.textContent=fmt(target*e); if(p<1) requestAnimationFrame(step);}
  requestAnimationFrame(step);
});
"""

st.markdown("<style>" + CSS_HALAMAN + "</style>", unsafe_allow_html=True)


# =====================================================================
# LOAD DATA
# =====================================================================
@st.cache_data
def load_data():
    df = pd.read_parquet(FILE_DATA)
    hilang = [k for k in KOLOM_WAJIB if k not in df.columns]
    if hilang:
        raise ValueError(f"Kolom berikut tidak ada di file data: {hilang}. "
                         "Pastikan parquet dibuat dari CSV hasil cleaning terbaru.")
    if 'BULAN' not in df.columns:
        df['BULAN'] = df['MONTH'].map(dict(zip(range(1, 13), URUTAN_BULAN)))

    df['maskapai'] = (df['OP_UNIQUE_CARRIER'].map(NAMA_MASKAPAI)
                      .fillna(df['OP_UNIQUE_CARRIER']) + " (" + df['OP_UNIQUE_CARRIER'] + ")")

    koordinat = pd.read_csv(FILE_KOORDINAT, keep_default_na=False)
    koordinat = koordinat[koordinat['IATA'].str.len() == 3].drop_duplicates('IATA')
    lat = koordinat.set_index('IATA')['Latitude']
    lon = koordinat.set_index('IATA')['Longitude']
    df['origin_lat'], df['origin_lon'] = df['ORIGIN'].map(lat), df['ORIGIN'].map(lon)
    df['dest_lat'], df['dest_lon'] = df['DEST'].map(lat), df['DEST'].map(lon)

    # Kota kembar (mis. Columbus di beberapa state) diberi label + state
    if {'origin_state', 'dest_state'}.issubset(df.columns):
        asal = df[['origin_city', 'origin_state']].set_axis(['kota', 'state'], axis=1)
        tujuan = df[['dest_city', 'dest_state']].set_axis(['kota', 'state'], axis=1)
        jml = pd.concat([asal, tujuan]).drop_duplicates().groupby('kota')['state'].nunique()
        kembar = set(jml[jml > 1].index)
        df['origin_label'] = df['origin_city'].where(
            ~df['origin_city'].isin(kembar), df['origin_city'] + " (" + df['origin_state'] + ")")
        df['dest_label'] = df['dest_city'].where(
            ~df['dest_city'].isin(kembar), df['dest_city'] + " (" + df['dest_state'] + ")")
    else:
        df['origin_label'], df['dest_label'] = df['origin_city'], df['dest_city']
    return df


# =====================================================================
# FUNGSI BANTU: TAMPILAN
# =====================================================================
def hero(judul, subjudul):
    st.markdown(f"<div class='hero'><span class='pesawat'>✈</span>"
                f"<h1>{judul}</h1><p>{subjudul}</p></div>", unsafe_allow_html=True)


def narasi(teks):
    aman = html.escape(teks)
    aman = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", aman)
    aman = re.sub(r"\*(.+?)\*", r"<i>\1</i>", aman)
    st.markdown(f"<div class='insight'>💡 <b>Insight:</b> {aman}</div>", unsafe_allow_html=True)


def tampil(fig):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#DFF4E8" if GELAP else "#12372A"),
                      margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, **LEBAR_PENUH)


def legenda_warna(skala, label_rendah="Rendah", label_tinggi="Tinggi"):
    """Strip gradient kecil supaya pembaca langsung paham arti skala warna sebuah grafik."""
    gradasi = ", ".join(skala)
    st.markdown(
        f"<div class='legenda'><span>{label_rendah}</span>"
        f"<span class='strip' style='background:linear-gradient(90deg,{gradasi})'></span>"
        f"<span>{label_tinggi}</span></div>", unsafe_allow_html=True)


def badge_sinyal(rawan):
    """Badge kecil merah (rawan delay) / hijau (tepat waktu), pelengkap warna supaya sinyalnya ganda (teks + warna)."""
    return "⚠ Rawan delay" if rawan else "✓ Tepat waktu"


def atur_animasi(fig, durasi=900):
    """Perlambat animasi supaya perubahan antarbulan terbaca, dan selaraskan warna tombol Play/slider dengan tema."""
    try:
        args = fig.layout.updatemenus[0].buttons[0].args[1]
        args["frame"]["duration"] = durasi
        args["transition"]["duration"] = durasi // 2
        fig.layout.updatemenus[0].bgcolor = HIJAU_MUDA
        fig.layout.updatemenus[0].bordercolor = HIJAU_TUA
        fig.layout.updatemenus[0].font = dict(color="#0B5D3B")
    except Exception:
        pass
    try:
        fig.layout.sliders[0].bgcolor = HIJAU_MUDA
        fig.layout.sliders[0].bordercolor = HIJAU_TUA
        fig.layout.sliders[0].activebgcolor = HIJAU_TUA
        fig.layout.sliders[0].font = dict(color="#0B5D3B" if not GELAP else "#DFF4E8")
    except Exception:
        pass


def kpi_row(items):
    """items: list (judul, nilai, desimal, akhiran[, warna]). Nilai angka -> animasi hitung naik;
    nilai teks -> ditampilkan apa adanya. warna opsional: kode hex (default hijau brand)."""
    kartu = ""
    for i, item in enumerate(items):
        judul, nilai, des, akh = item[:4]
        warna = item[4] if len(item) > 4 else ("#6FE3A3" if GELAP else "#0B5D3B")
        if isinstance(nilai, str):
            isi = f'<span style="color:{warna}">{html.escape(nilai)}</span>'
        elif nilai != nilai:
            isi = f'<span style="color:{warna}">n/a</span>'
        else:
            isi = (f'<span style="color:{warna}"><span class="n" data-v="{nilai}" data-d="{des}">0</span>'
                   f'{akh}</span>')
        kartu += (f'<div class="k" style="animation-delay:{i * 0.12}s">'
                  f'<div class="t">{html.escape(judul)}</div><div class="v">{isi}</div></div>')
    components.html(f"<style>{CSS_KARTU}</style><div class='row'>{kartu}</div>"
                    f"<script>{JS_HITUNG}</script>", height=115)


def salju_sekali(bulan):
    """Salju hanya muncul saat pengguna baru memilih Nov/Des (bukan tiap rerun)."""
    if bulan in ('Nov', 'Des') and st.session_state.get('salju_bulan') != bulan:
        st.snow()
    st.session_state['salju_bulan'] = bulan


# =====================================================================
# FUNGSI BANTU: DATA
# =====================================================================
def hitung_kpi(data):
    total = data['total_flights'].sum()
    kursi = data['total_seats'].sum()
    return {
        'total_flights': total,
        'avg_delay': (data['avg_arr_delay'] * data['total_flights']).sum() / total,
        'delay_rate': data['delayed_flights'].sum() / total * 100,
        'load_factor': (data['total_passengers'].sum() / kursi * 100) if kursi > 0 else float('nan'),
    }


def ringkas(data, by):
    """Ringkasan berbobot jumlah penerbangan (data sudah teragregasi)."""
    d = data.assign(_delay_total=data['avg_arr_delay'] * data['total_flights'])
    g = d.groupby(by).agg(
        total_flights=('total_flights', 'sum'),
        delayed_flights=('delayed_flights', 'sum'),
        _delay_total=('_delay_total', 'sum'),
        penumpang=('total_passengers', 'sum'),
        kursi=('total_seats', 'sum'),
    ).reset_index()
    g['avg_delay'] = g['_delay_total'] / g['total_flights']
    g['delay_rate'] = g['delayed_flights'] / g['total_flights'] * 100
    g['load_factor'] = g['penumpang'] / g['kursi'].replace(0, float('nan')) * 100
    return g.drop(columns=['_delay_total'])


def urutkan_bulan(tabel):
    tabel = tabel.copy()
    tabel['BULAN'] = pd.Categorical(tabel['BULAN'], categories=URUTAN_BULAN, ordered=True)
    return tabel.sort_values('BULAN')


def fmt_metrik(kolom, nilai):
    return f"{nilai:.1f}%" if kolom == 'delay_rate' else f"{nilai:.1f} menit"


def fmt_selisih(kolom, nilai):
    return f"{nilai:.1f} poin persentase" if kolom == 'delay_rate' else f"{nilai:.1f} menit"


def bulan_tersedia(data):
    ada = set(data['BULAN'].unique())
    return [b for b in URUTAN_BULAN if b in ada]


def teks_periode(tahun):
    tahun = sorted(tahun)
    return str(tahun[0]) if len(tahun) == 1 else f"{tahun[0]}–{tahun[-1]}"


# =====================================================================
# HALAMAN 1: RINGKASAN DELAY
# =====================================================================
def halaman_ringkasan(data):
    hero("Ringkasan Ketepatan Waktu Penerbangan",
         "Seberapa tepat waktu penerbangan domestik Amerika Serikat?")

    kpi = hitung_kpi(data)
    kpi_row([("Persentase Delay (>15 menit)", kpi['delay_rate'], 1, "%", warna_kpi('delay_rate', kpi['delay_rate'])),
             ("Rata-rata Delay", kpi['avg_delay'], 1, " menit", warna_kpi('avg_delay', kpi['avg_delay'])),
             ("Total Penerbangan", kpi['total_flights'], 0, ""),
             ("Rata-rata Load Factor", kpi['load_factor'], 1, "%")])

    with st.expander("Cara membaca metrik delay"):
        st.markdown(
            "- **Persentase delay**: porsi penerbangan yang tiba terlambat lebih dari 15 menit "
            "(mengacu pada ambang 15 menit BTS/FAA). Tidak terpengaruh penerbangan yang terlambat ekstrem, "
            "sehingga dijadikan metrik utama.\n"
            "- **Rata-rata delay**: rata-rata berbobot jumlah penerbangan (bukan median). Bisa tertarik naik "
            "oleh penerbangan yang terlambat berjam-jam, jadi dibaca bersama persentase delay.\n"
            "- **Load factor**: persentase kursi terisi (total penumpang ÷ total kursi).")

    pilihan = st.radio("Tampilkan berdasarkan:", list(METRIK.keys()), horizontal=True)
    kolom, label = METRIK[pilihan]

    # ----- Grafik 1: per maskapai -----
    st.subheader("Delay per Maskapai")
    legenda_warna(SKALA_DELAY, "Aman", "Rawan delay")
    per_maskapai = ringkas(data, 'maskapai').sort_values(kolom, ascending=True)
    fig1 = px.bar(per_maskapai, x=kolom, y='maskapai', orientation='h', color=kolom,
                  color_continuous_scale=SKALA_DELAY,
                  hover_data={'total_flights': ':,.0f', 'delay_rate': ':.1f', 'avg_delay': ':.1f'},
                  labels={kolom: label, 'maskapai': 'Maskapai', 'total_flights': 'Total penerbangan',
                          'delay_rate': 'Delay (%)', 'avg_delay': 'Rata-rata delay (mnt)'})
    fig1.update_layout(coloraxis_showscale=False)
    tampil(fig1)
    atas, bawah = per_maskapai.iloc[-1], per_maskapai.iloc[0]
    narasi(f"Delay tertinggi dialami **{atas['maskapai']}** ({fmt_metrik(kolom, atas[kolom])}), "
           f"sedangkan yang paling tepat waktu adalah **{bawah['maskapai']}** ({fmt_metrik(kolom, bawah[kolom])}). "
           f"Selisihnya {fmt_selisih(kolom, atas[kolom] - bawah[kolom])}. "
           f"Sebagai pembanding, rata-rata seluruh maskapai adalah {fmt_metrik(kolom, kpi[kolom])}.")

    # ----- Grafik 2: tren per bulan -----
    st.subheader("Tren Delay per Bulan")
    per_bulan = urutkan_bulan(ringkas(data, 'BULAN'))
    fig2 = px.line(per_bulan, x='BULAN', y=kolom, markers=True,
                   color_discrete_sequence=[MERAH_BAHAYA],
                   category_orders={'BULAN': URUTAN_BULAN}, labels={kolom: label, 'BULAN': 'Bulan'})
    fig2.update_traces(fill='tozeroy', fillcolor='rgba(232,85,42,.10)')
    tampil(fig2)
    tinggi, rendah = per_bulan.loc[per_bulan[kolom].idxmax()], per_bulan.loc[per_bulan[kolom].idxmin()]
    narasi(f"Delay paling parah terjadi pada bulan **{tinggi['BULAN']}** ({fmt_metrik(kolom, tinggi[kolom])}) "
           f"dan paling lancar pada **{rendah['BULAN']}** ({fmt_metrik(kolom, rendah[kolom])}), "
           f"selisih {fmt_selisih(kolom, tinggi[kolom] - rendah[kolom])}. "
           "Lihat menu *Penyebab Dominan Delay* untuk faktor di baliknya.")

    # ----- Grafik 3: animasi bar per bulan -----
    st.subheader("Delay Maskapai dari Bulan ke Bulan")
    anim = urutkan_bulan(ringkas(data, ['BULAN', 'maskapai']))
    anim['BULAN'] = anim['BULAN'].astype(str)
    fig3 = px.bar(anim, x=kolom, y='maskapai', orientation='h', color=kolom,
                  color_continuous_scale=SKALA_DELAY,
                  animation_frame='BULAN', range_x=[0, anim[kolom].max() * 1.15],
                  range_color=[0, anim[kolom].max()],
                  category_orders={'BULAN': bulan_tersedia(data),
                                   # Bar beranimasi menyusun kategori terbalik dibanding bar statis,
                                   # jadi urutannya dibalik di sini supaya kedua grafik konsisten.
                                   'maskapai': per_maskapai['maskapai'].tolist()[::-1]},
                  labels={kolom: label, 'maskapai': 'Maskapai', 'BULAN': 'Bulan'})
    fig3.update_layout(coloraxis_showscale=False)
    atur_animasi(fig3)
    tampil(fig3)
    pv = anim.pivot(index='maskapai', columns='BULAN', values=kolom)
    goyang = (pv.max(axis=1) - pv.min(axis=1)).idxmax()
    narasi(f"**{goyang}** paling berubah-ubah sepanjang tahun: terbaik pada bulan **{pv.loc[goyang].idxmin()}** "
           f"({fmt_metrik(kolom, pv.loc[goyang].min())}) dan terburuk pada **{pv.loc[goyang].idxmax()}** "
           f"({fmt_metrik(kolom, pv.loc[goyang].max())}). Urutan maskapai pada grafik tetap, "
           "yang bergerak adalah panjang batangnya.")

    # ----- Grafik 4: heatmap bulan x maskapai -----
    st.subheader("Peta Panas Delay: Maskapai × Bulan")
    legenda_warna(SKALA_DELAY, "Aman", "Rawan delay")
    pivot = urutkan_bulan(ringkas(data, ['BULAN', 'maskapai'])).pivot(index='maskapai', columns='BULAN', values=kolom)
    pivot = pivot.reindex(columns=[b for b in URUTAN_BULAN if b in pivot.columns])
    fig4 = px.imshow(pivot, color_continuous_scale=SKALA_DELAY, aspect='auto',
                     labels=dict(x="Bulan", y="Maskapai", color=label))
    fig4.update_layout(coloraxis_showscale=False)
    tampil(fig4)
    sel = pivot.max(axis=1) - pivot.min(axis=1)
    mv = sel.idxmax()
    narasi(f"Rentang {label.lower()} terlebar dimiliki **{mv}**: dari {fmt_metrik(kolom, pivot.loc[mv].min())} "
           f"hingga {fmt_metrik(kolom, pivot.loc[mv].max())} tergantung bulannya — pola yang tidak terlihat "
           "kalau cuma melihat rata-rata keseluruhan.")

# =====================================================================
# HALAMAN 2: PENYEBAB DOMINAN DELAY
# =====================================================================
def halaman_penyebab(data):
    hero("Faktor Penyebab Delay Dominan", "Apa yang paling sering membuat penerbangan terlambat?")
    st.caption("BTS mencatat rincian penyebab hanya untuk penerbangan yang terlambat 15 menit atau lebih. "
               "Angka di bawah adalah total menit delay menurut penyebabnya.")

    kolom_p = list(LABEL_PENYEBAB.keys())
    total = data[kolom_p].sum().rename(index=LABEL_PENYEBAB).sort_values(ascending=False)
    grand = total.sum()
    if grand == 0:
        st.warning("Tidak ada data penyebab delay pada filter ini.")
        return

    fig1 = px.pie(values=total.values, names=total.index, hole=0.45, color=total.index,
                  color_discrete_map=WARNA_PENYEBAB,
                  title="Proporsi Total Menit Delay Berdasarkan Penyebab")
    tampil(fig1)
    porsi = total / grand * 100
    narasi(f"Penyebab terbesar adalah **{total.index[0]}** ({porsi.iloc[0]:.1f}% dari seluruh menit delay), "
           f"diikuti **{total.index[1]}** ({porsi.iloc[1]:.1f}%). Keduanya menyumbang {porsi.iloc[:2].sum():.1f}%. "
           f"Faktor **{total.index[-1]}** hampir tidak berperan ({porsi.iloc[-1]:.2f}%).")

    st.subheader("Rincian (menit)")
    st.dataframe(pd.DataFrame({'Penyebab': total.index,
                               'Total Menit': total.map('{:,.0f}'.format).values,
                               'Persentase': porsi.map('{:.1f}%'.format).values}), hide_index=True)

    st.subheader("Komposisi Penyebab Delay per Bulan")
    per_bulan = data.groupby('BULAN')[kolom_p].sum().rename(columns=LABEL_PENYEBAB)
    per_bulan = per_bulan.reindex(bulan_tersedia(data))
    panjang = per_bulan.reset_index().melt(id_vars='BULAN', var_name='Penyebab', value_name='Menit')
    fig2 = px.bar(panjang, x='BULAN', y='Menit', color='Penyebab',
                  color_discrete_map=WARNA_PENYEBAB,
                  category_orders={'BULAN': URUTAN_BULAN, 'Penyebab': list(WARNA_PENYEBAB.keys())},
                  labels={'BULAN': 'Bulan', 'Menit': 'Total menit delay'})
    tampil(fig2)
    porsi_cuaca = (per_bulan['Cuaca'] / per_bulan.sum(axis=1) * 100).dropna()
    b_cuaca = porsi_cuaca.idxmax()
    narasi(f"Total menit delay terbesar terjadi pada bulan **{per_bulan.sum(axis=1).idxmax()}**. "
           f"Faktor cuaca punya porsi terbesar pada bulan **{b_cuaca}** ({porsi_cuaca[b_cuaca]:.1f}% dari menit "
           "delay bulan tersebut), sedangkan bulan lain lebih didominasi faktor maskapai dan keterlambatan "
           "pesawat sebelumnya.")


# =====================================================================
# HALAMAN 3: BANDARA & BULAN TERSIBUK
# =====================================================================
def top_bandara(data):
    t = (data.groupby(['ORIGIN', 'origin_label'])['total_flights'].sum().reset_index()
         .sort_values('total_flights', ascending=False).head(10))
    t['bandara'] = t['origin_label'] + " (" + t['ORIGIN'] + ")"
    return t


def halaman_tersibuk(data):
    hero("Bandara & Bulan Tersibuk", "Kapan dan di mana lalu lintas udara paling padat?")
    st.caption("Volume dihitung dari jumlah penerbangan yang berangkat dari bandara tersebut.")
    total_semua = data['total_flights'].sum()

    st.subheader("Top 10 Bandara Tersibuk")
    legenda_warna(SKALA_VOLUME, "Sepi", "Ramai")
    bandara = top_bandara(data)
    fig1 = px.bar(bandara.sort_values('total_flights'), x='total_flights', y='bandara', orientation='h',
                  color='total_flights', labels={'total_flights': 'Total Penerbangan', 'bandara': 'Bandara'})
    fig1.update_layout(coloraxis_showscale=False)
    tampil(fig1)
    t = bandara.iloc[0]
    narasi(f"**{t['bandara']}** adalah bandara tersibuk dengan {t['total_flights']:,.0f} penerbangan "
           f"({t['total_flights'] / total_semua * 100:.1f}% dari seluruh penerbangan). Sepuluh bandara teratas "
           f"menangani {bandara['total_flights'].sum() / total_semua * 100:.1f}% dari total, artinya lalu lintas "
           "udara sangat terpusat di sedikit bandara besar.")

    st.subheader("Volume Penerbangan per Bulan")
    per_bulan = urutkan_bulan(data.groupby('BULAN')['total_flights'].sum().reset_index())
    fig2 = px.bar(per_bulan, x='BULAN', y='total_flights', color='total_flights',
                  category_orders={'BULAN': URUTAN_BULAN},
                  labels={'total_flights': 'Total Penerbangan', 'BULAN': 'Bulan'})
    tampil(fig2)
    ramai, sepi = per_bulan.loc[per_bulan['total_flights'].idxmax()], per_bulan.loc[per_bulan['total_flights'].idxmin()]
    narasi(f"Bulan tersibuk adalah **{ramai['BULAN']}** ({ramai['total_flights']:,.0f} penerbangan) dan paling sepi "
           f"**{sepi['BULAN']}** ({sepi['total_flights']:,.0f}). Bulan tersibuk "
           f"{(ramai['total_flights'] / sepi['total_flights'] - 1) * 100:.1f}% lebih ramai daripada bulan tersepi.")

    st.subheader("Kepadatan Penerbangan per Bulan")
    peta = urutkan_bulan(data.groupby(['BULAN', 'ORIGIN', 'origin_lat', 'origin_lon'])['total_flights']
                         .sum().reset_index())
    peta['BULAN'] = peta['BULAN'].astype(str)
    skala = [[0, "rgba(255,189,94,0)"], [0.35, SKALA_VOLUME[2]], [1, SKALA_VOLUME[4]]]
    fig_peta = px.density_map(peta, lat='origin_lat', lon='origin_lon', z='total_flights', radius=RADIUS_PETA,
                              animation_frame='BULAN', category_orders={'BULAN': bulan_tersedia(data)},
                              center=dict(lat=39, lon=-98), zoom=3, map_style=GAYA_PETA,
                              range_color=[0, peta['total_flights'].max()], opacity=0.9 if GELAP else 0.8,
                              color_continuous_scale=skala, labels={'total_flights': 'Penerbangan'})
    atur_animasi(fig_peta, 1100)
    fig_peta.update_layout(height=520)
    tampil(fig_peta)
    narasi(f"Kepadatan nasional memuncak pada bulan **{ramai['BULAN']}**. Pada bulan itu, bandara yang paling sibuk "
           f"adalah **{top_bandara(data[data['BULAN'] == ramai['BULAN']]).iloc[0]['bandara']}**. "
           "Titik-titik terang pada peta umumnya adalah kota hub besar.")

    st.subheader("Bandara Tersibuk pada Bulan Tertentu")
    bulan_pilih = st.selectbox("Pilih Bulan:", bulan_tersedia(data))
    salju_sekali(bulan_pilih)
    top_b = top_bandara(data[data['BULAN'] == bulan_pilih])
    fig3 = px.bar(top_b.sort_values('total_flights'), x='total_flights', y='bandara', orientation='h',
                  color='total_flights', labels={'total_flights': 'Total Penerbangan', 'bandara': 'Bandara'})
    fig3.update_layout(coloraxis_showscale=False)
    tampil(fig3)
    tiga = top_b['bandara'].head(3).tolist()
    narasi(f"Pada bulan **{bulan_pilih}**, tiga bandara tersibuk adalah " + ", ".join(f"**{x}**" for x in tiga) + ".")

    st.subheader("Bandara Paling Rawan vs Paling Tepat Waktu")
    st.caption("Hanya bandara dengan minimal 20.000 penerbangan yang dibandingkan, agar hasilnya representatif.")
    bdr = ringkas(data, 'origin_label')
    bdr = bdr[bdr['total_flights'] >= 20000].sort_values('delay_rate', ascending=False)
    if len(bdr) >= 2:
        c1, c2 = st.columns(2)
        fmt_tbl = lambda t: t.rename(columns={'origin_label': 'Bandara', 'delay_rate': '% Delay',
                                              'total_flights': 'Total Penerbangan'}).style.format(
            {'% Delay': '{:.1f}%', 'Total Penerbangan': '{:,.0f}'})
        with c1:
            st.markdown("**5 Paling Rawan Delay**")
            st.dataframe(fmt_tbl(bdr.head(5)[['origin_label', 'delay_rate', 'total_flights']]), hide_index=True)
        with c2:
            st.markdown("**5 Paling Tepat Waktu**")
            st.dataframe(fmt_tbl(bdr.tail(5)[['origin_label', 'delay_rate', 'total_flights']].iloc[::-1]),
                        hide_index=True)
        narasi(f"**{bdr.iloc[0]['origin_label']}** paling rawan delay ({bdr.iloc[0]['delay_rate']:.1f}%) di antara "
               f"bandara besar (≥20.000 penerbangan), sedangkan **{bdr.iloc[-1]['origin_label']}** paling tepat "
               f"waktu ({bdr.iloc[-1]['delay_rate']:.1f}%).")
    else:
        st.info("Belum cukup bandara dengan ≥20.000 penerbangan pada filter ini untuk dibandingkan.")


# =====================================================================
# HALAMAN 4: CEK RUTE (A KE B)
# =====================================================================
def peta_jaringan(data, asal, tujuan):
    sub = data[data['origin_label'] == asal]
    utama = sub.groupby(['ORIGIN', 'origin_lat', 'origin_lon'])['total_flights'].sum()
    if utama.empty:
        st.info("Koordinat bandara asal tidak tersedia, sehingga peta tidak ditampilkan.")
        return
    kode_o, o_lat, o_lon = utama.idxmax()
    jar = sub.groupby(['DEST', 'dest_label', 'dest_lat', 'dest_lon'])['total_flights'].sum().reset_index()
    jar = pd.concat([jar.nlargest(40, 'total_flights'), jar[jar['dest_label'] == tujuan]]).drop_duplicates('DEST')
    maks = jar['total_flights'].max()

    fig = go.Figure()
    for _, r in jar.iterrows():
        sorot = r['dest_label'] == tujuan
        fig.add_trace(go.Scattermap(
            lat=[o_lat, r['dest_lat']], lon=[o_lon, r['dest_lon']], mode='lines',
            line=dict(width=6 if sorot else 1 + 4 * r['total_flights'] / maks,
                      color=HIJAU_TUA if sorot else HIJAU_MUDA),
            opacity=1 if sorot else (0.75 if GELAP else 0.55), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scattermap(
        lat=jar['dest_lat'], lon=jar['dest_lon'], mode='markers', showlegend=False,
        marker=dict(size=8, color=HIJAU), hoverinfo='text',
        text=jar['dest_label'] + " (" + jar['DEST'] + "): " + jar['total_flights'].map('{:,.0f}'.format) + " penerbangan"))
    fig.add_trace(go.Scattermap(
        lat=[o_lat], lon=[o_lon], mode='markers', showlegend=False, hoverinfo='text',
        marker=dict(size=16, color=HIJAU_TUA), text=f"{asal} ({kode_o}) - kota asal"))
    fig.update_layout(map_style=GAYA_PETA, map_center=dict(lat=39, lon=-98),
                      map_zoom=3, height=560,
                      title=f"Jaringan rute dari {asal} (garis tebal gelap = rute pilihanmu)")
    tampil(fig)

    semua = sub.groupby('dest_label')['total_flights'].sum().sort_values(ascending=False)
    if tujuan in semua.index:
        narasi(f"Dari **{asal}** terdapat **{len(semua)}** kota tujuan. Tujuan tersibuk adalah **{semua.index[0]}** "
               f"({semua.iloc[0]:,.0f} penerbangan). Rute ke **{tujuan}** berada di peringkat "
               f"**{list(semua.index).index(tujuan) + 1}** dari {len(semua)} tujuan berdasarkan jumlah penerbangan.")


def halaman_rute(data):
    hero("Cek Pola Rute Penerbangan", "Pilih maskapai paling tepat waktu untuk rutemu")

    if 'rute_asal' not in st.session_state:
        st.session_state['rute_asal'] = "Atlanta"
    if 'rute_tujuan' not in st.session_state:
        st.session_state['rute_tujuan'] = None

    bc1, bc2, _ = st.columns(3)
    if bc1.button("🔥 Rute Terpadat"):
        top_rute = data.groupby(['origin_label', 'dest_label'])['total_flights'].sum().idxmax()
        st.session_state['rute_asal'], st.session_state['rute_tujuan'] = top_rute
    if bc2.button("🔁 Tukar Asal ↔ Tujuan") and st.session_state.get('rute_tujuan'):
        st.session_state['rute_asal'], st.session_state['rute_tujuan'] = (
            st.session_state['rute_tujuan'], st.session_state['rute_asal'])

    daftar_asal = sorted(data['origin_label'].unique())
    c1, c2, c3 = st.columns(3)
    asal_awal = st.session_state['rute_asal'] if st.session_state['rute_asal'] in daftar_asal else daftar_asal[0]
    asal = c1.selectbox("Dari Kota:", daftar_asal, index=daftar_asal.index(asal_awal))
    st.session_state['rute_asal'] = asal

    opsi_tujuan = sorted(data.loc[data['origin_label'] == asal, 'dest_label'].unique())
    # Default tujuan = rute paling padat dari kota asal ini, bukan abjad pertama -- supaya kesan pertama tidak sepi.
    tersibuk_tujuan = (data[data['origin_label'] == asal].groupby('dest_label')['total_flights']
                       .sum().idxmax()) if opsi_tujuan else None
    tujuan_sesi = st.session_state.get('rute_tujuan')
    tujuan_awal = tujuan_sesi if tujuan_sesi in opsi_tujuan else tersibuk_tujuan
    tujuan = c2.selectbox("Ke Kota:", opsi_tujuan,
                          index=opsi_tujuan.index(tujuan_awal) if tujuan_awal in opsi_tujuan else 0)
    st.session_state['rute_tujuan'] = tujuan

    bulan_pilih = c3.selectbox("Bulan (untuk peringkat):", ["Semua bulan"] + bulan_tersedia(data))
    salju_sekali(bulan_pilih)

    rute = data[(data['origin_label'] == asal) & (data['dest_label'] == tujuan)]
    if rute.empty:
        st.warning("Tidak ada data penerbangan untuk rute ini pada tahun yang difilter.")
        return

    kpi = hitung_kpi(rute)
    kpi_row([("Total Penerbangan", kpi['total_flights'], 0, ""),
             ("Persentase Delay (>15 menit)", kpi['delay_rate'], 1, "%", warna_kpi('delay_rate', kpi['delay_rate'])),
             ("Rata-rata Delay", kpi['avg_delay'], 1, " menit", warna_kpi('avg_delay', kpi['avg_delay'])),
             ("Bulan Tersibuk", rute.groupby('BULAN')['total_flights'].sum().idxmax(), 0, "")])

    # ----- Peringkat maskapai -----
    ket = "sepanjang tahun" if bulan_pilih == "Semua bulan" else f"bulan {bulan_pilih}"
    st.subheader(f"Peringkat Maskapai: {asal} → {tujuan} ({ket})")
    st.caption(f"Diurutkan dari persentase delay terendah. Maskapai dengan kurang dari {MIN_PENERBANGAN} "
               "penerbangan ditampilkan di bawah tanpa peringkat karena angkanya belum stabil. "
               "Angka merupakan gabungan tahun yang dipilih pada filter.")
    data_rank = rute if bulan_pilih == "Semua bulan" else rute[rute['BULAN'] == bulan_pilih]

    if data_rank.empty:
        st.warning(f"Tidak ada penerbangan untuk rute ini pada bulan {bulan_pilih}.")
    else:
        rank = ringkas(data_rank, 'maskapai')
        rank['cukup'] = rank['total_flights'] >= MIN_PENERBANGAN
        rank = (rank.sort_values(['cukup', 'delay_rate', 'avg_delay'], ascending=[False, True, True])
                .head(10).reset_index(drop=True))
        n_cukup = int(rank['cukup'].sum())

        idx_cukup = rank.index[rank['cukup']].tolist()
        sinyal = [""] * len(rank)
        if idx_cukup:
            sinyal[idx_cukup[0]] = badge_sinyal(False)
            if len(idx_cukup) > 1:
                sinyal[idx_cukup[-1]] = badge_sinyal(True)

        tabel_peringkat = pd.DataFrame({
            'Peringkat': [str(i + 1) if ok else "–" for i, ok in enumerate(rank['cukup'])],
            'Maskapai': rank['maskapai'],
            'Total Penerbangan': rank['total_flights'],
            '% Delay (>15 mnt)': rank['delay_rate'],
            'Rata-rata Delay (mnt)': rank['avg_delay'],
            'Load Factor': rank['load_factor'],
            'Sinyal': sinyal,
            'Catatan': ["" if ok else "Data terbatas" for ok in rank['cukup']],
        })

        acuan_nasional = hitung_kpi(data)['delay_rate']  # patokan absolut, bukan relatif antarbaris tabel ini

        def _warna_delay(nilai):
            """Heatmap manual (krem->merah), diukur terhadap rata-rata nasional -- bukan relatif antarbaris."""
            if pd.isna(nilai):
                return ""
            rasio = nilai / acuan_nasional if acuan_nasional else 1
            t = max(0, min(1, (rasio - 0.5) / 1.3))  # 0.5x nasional -> 0 (aman), 1.8x nasional -> 1 (rawan)
            n = len(SKALA_DELAY) - 1
            pos = t * n
            i = min(int(pos), n - 1)
            frac = pos - i
            c1 = tuple(int(SKALA_DELAY[i][j:j + 2], 16) for j in (1, 3, 5))
            c2 = tuple(int(SKALA_DELAY[i + 1][j:j + 2], 16) for j in (1, 3, 5))
            rgb = tuple(round(c1[k] + (c2[k] - c1[k]) * frac) for k in range(3))
            teks = "#FFFFFF" if t > 0.55 else "#3D2B1F"
            return f"background-color:rgb{rgb};color:{teks}"

        styler = tabel_peringkat.style.hide(axis="index").format({
            'Total Penerbangan': '{:,.0f}'.format,
            '% Delay (>15 mnt)': '{:.1f}%'.format,
            'Rata-rata Delay (mnt)': '{:.1f}'.format,
            'Load Factor': lambda v: f"{v:.1f}%" if pd.notna(v) else "n/a",
        })
        try:
            styler = styler.map(_warna_delay, subset=['% Delay (>15 mnt)'])
        except AttributeError:
            styler = styler.applymap(_warna_delay, subset=['% Delay (>15 mnt)'])
        st.dataframe(styler, hide_index=True)
        st.caption(f"Warna kolom % Delay: krem = jauh di bawah rata-rata nasional ({acuan_nasional:.1f}%), "
                   "merah tegas = jauh di atasnya -- ambang tetap, bukan relatif antarbaris di tabel ini.")
        st.download_button("⬇ Unduh peringkat (CSV)", tabel_peringkat.to_csv(index=False).encode('utf-8'),
                           file_name=f"peringkat_{asal}_{tujuan}.csv", mime="text/csv")

        rp = rank.iloc[::-1].copy()
        rp['label'] = rp['delay_rate'].map('{:.1f}%'.format)
        tinggi_chart = max(220, 50 + 42 * len(rp))
        fig_rank = px.bar(rp, x='delay_rate', y='maskapai', orientation='h', color='delay_rate',
                          color_continuous_scale=SKALA_DELAY, text='label',
                          labels={'delay_rate': 'Penerbangan delay (%)', 'maskapai': 'Maskapai'})
        fig_rank.update_traces(marker=dict(opacity=rp['cukup'].map({True: 1.0, False: 0.4}).tolist()))
        fig_rank.update_layout(height=tinggi_chart, coloraxis_showscale=False)
        tampil(fig_rank)
        st.caption("Batang pudar = data terbatas (kurang dari 30 penerbangan).")

        if n_cukup == 0:
            narasi(f"Belum ada maskapai dengan minimal {MIN_PENERBANGAN} penerbangan pada rute dan bulan ini, "
                   "sehingga peringkat yang andal belum bisa dibuat. Coba pilih *Semua bulan* atau aktifkan "
                   "kedua tahun pada filter.")
        else:
            layak = rank[rank['cukup']]
            b = layak.iloc[0]
            if n_cukup >= 2:
                w_badge = layak.iloc[-1]
                st.markdown(
                    f"<span class='badge-aman'>✓ {html.escape(b['maskapai'])}</span>&nbsp;&nbsp;"
                    f"<span class='badge-bahaya'>⚠ {html.escape(w_badge['maskapai'])}</span>",
                    unsafe_allow_html=True)
            teks = (f"Untuk rute {asal} → {tujuan} ({ket}), maskapai paling tepat waktu adalah **{b['maskapai']}** "
                    f"({b['delay_rate']:.1f}% penerbangan delay dari {b['total_flights']:,.0f} penerbangan).")
            if n_cukup >= 2:
                w = layak.iloc[-1]
                teks += (f" Yang paling sering delay adalah **{w['maskapai']}** ({w['delay_rate']:.1f}%), "
                         f"selisih {w['delay_rate'] - b['delay_rate']:.1f} poin persentase.")
                lf = layak.dropna(subset=['load_factor'])
                if not lf.empty and (lf['load_factor'].max() - lf['load_factor'].min()) >= 3:
                    s = lf.sort_values('load_factor').iloc[0]
                    teks += (f" Jika ingin penerbangan yang lebih lengang, **{s['maskapai']}** punya rata-rata "
                             f"load factor terendah ({s['load_factor']:.1f}%).")
            else:
                teks += " Hanya satu maskapai yang memenuhi batas minimal data, jadi belum ada pembanding."
            if n_cukup < len(rank):
                teks += f" Maskapai berlabel abu-abu punya data kurang dari {MIN_PENERBANGAN} penerbangan."
            narasi(teks)

    # ----- Peta jaringan rute -----
    st.subheader("Peta Jaringan Rute")
    peta_jaringan(data, asal, tujuan)

    # ----- Per bulan untuk rute ini -----
    st.subheader("Volume Penerbangan per Bulan untuk Rute Ini")
    vol = urutkan_bulan(rute.groupby('BULAN')['total_flights'].sum().reset_index())
    tampil(px.bar(vol, x='BULAN', y='total_flights', color='total_flights',
                  category_orders={'BULAN': URUTAN_BULAN},
                  labels={'total_flights': 'Total Penerbangan', 'BULAN': 'Bulan'}))
    ramai, sepi = vol.loc[vol['total_flights'].idxmax()], vol.loc[vol['total_flights'].idxmin()]
    narasi(f"Rute ini paling ramai pada bulan **{ramai['BULAN']}** ({ramai['total_flights']:,.0f} penerbangan) dan "
           f"paling sepi pada **{sepi['BULAN']}** ({sepi['total_flights']:,.0f}). Memesan di bulan yang lebih sepi "
           "umumnya berarti pesawat lebih lengang.")

    st.subheader("Persentase Delay per Bulan untuk Rute Ini")
    dly = urutkan_bulan(ringkas(rute, 'BULAN'))
    tampil(px.line(dly, x='BULAN', y='delay_rate', markers=True, category_orders={'BULAN': URUTAN_BULAN},
                   labels={'delay_rate': 'Penerbangan delay (%)', 'BULAN': 'Bulan'}))
    ok = dly[dly['total_flights'] >= MIN_PENERBANGAN]
    if len(ok) >= 2:
        l, p = ok.loc[ok['delay_rate'].idxmin()], ok.loc[ok['delay_rate'].idxmax()]
        narasi(f"Bulan paling lancar untuk rute ini adalah **{l['BULAN']}** ({l['delay_rate']:.1f}% delay) dan paling "
               f"rawan delay **{p['BULAN']}** ({p['delay_rate']:.1f}%). Hanya bulan dengan minimal "
               f"{MIN_PENERBANGAN} penerbangan yang dibandingkan.")
    else:
        narasi(f"Data rute ini terlalu sedikit untuk membandingkan antarbulan (minimal {MIN_PENERBANGAN} penerbangan per bulan).")

# =====================================================================
# HALAMAN 0: BERANDA
# =====================================================================
def halaman_beranda(data):
    hero("Dashboard Ketepatan Waktu Penerbangan AS", "Ringkasan temuan paling penting dari data 2024-2025")
    kpi = hitung_kpi(data)
    per_bulan = ringkas(data, 'BULAN')
    b_buruk, b_baik = per_bulan.loc[per_bulan['delay_rate'].idxmax()], per_bulan.loc[per_bulan['delay_rate'].idxmin()]
    per_maskapai = ringkas(data, 'maskapai')
    m_buruk, m_baik = per_maskapai.loc[per_maskapai['delay_rate'].idxmax()], per_maskapai.loc[per_maskapai['delay_rate'].idxmin()]

    st.subheader("Temuan Utama")
    c1, c2 = st.columns(2)
    with c1:
        satu_dari = round(100 / kpi['delay_rate']) if kpi['delay_rate'] else 0
        st.markdown(f"<div class='insight'>✈ <b>1 dari {satu_dari} penerbangan terlambat</b> lebih dari 15 menit "
                    f"({kpi['delay_rate']:.1f}% dari {kpi['total_flights']:,.0f} penerbangan).</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='insight'>📅 Bulan <b>{b_buruk['BULAN']}</b> paling rawan delay "
                    f"({b_buruk['delay_rate']:.1f}%), jauh berbeda dari <b>{b_baik['BULAN']}</b> "
                    f"({b_baik['delay_rate']:.1f}%).</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='insight'>🏢 <b>{m_buruk['maskapai']}</b> paling sering delay "
                    f"({m_buruk['delay_rate']:.1f}%), sedangkan <b>{m_baik['maskapai']}</b> paling tepat waktu "
                    f"({m_baik['delay_rate']:.1f}%).</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='insight'>👥 Rata-rata kursi terisi (<b>load factor</b>): "
                    f"{kpi['load_factor']:.1f}%.</div>", unsafe_allow_html=True)

    st.subheader("Mulai Eksplorasi")
    if st.button("✈ Mulai cek rute penerbangan", type="primary"):
        st.session_state['menu_aktif'] = "Cek Rute (A ke B)"
        st.rerun()


# =====================================================================
# HALAMAN: MUSIM LIBUR (H3)
# =====================================================================
def halaman_musim(data):
    hero("Musim Liburan vs Bulan Biasa", "Menguji dugaan: apakah delay naik saat musim liburan?")
    libur = data[data['MONTH'].isin([11, 12])]
    biasa = data[~data['MONTH'].isin([11, 12])]
    if libur.empty or biasa.empty:
        st.info("Data musim liburan atau bulan biasa tidak tersedia pada filter saat ini.")
        return
    kl, kb = hitung_kpi(libur), hitung_kpi(biasa)

    kpi_row([("Delay Musim Liburan (Nov-Des)", kl['delay_rate'], 1, "%", warna_kpi('delay_rate', kl['delay_rate'])),
             ("Delay Bulan Biasa", kb['delay_rate'], 1, "%", warna_kpi('delay_rate', kb['delay_rate']))])

    fig = px.bar(pd.DataFrame({'Periode': ['Musim Liburan (Nov-Des)', 'Bulan Biasa'],
                               'delay_rate': [kl['delay_rate'], kb['delay_rate']]}),
                 x='Periode', y='delay_rate', color='delay_rate', color_continuous_scale=SKALA_DELAY,
                 text=[f"{kl['delay_rate']:.1f}%", f"{kb['delay_rate']:.1f}%"],
                 labels={'delay_rate': 'Penerbangan delay (%)'})
    fig.update_layout(coloraxis_showscale=False)
    tampil(fig)

    if kl['delay_rate'] < kb['delay_rate']:
        narasi(f"Berlawanan dengan dugaan awal (H3), musim liburan justru sedikit **lebih lancar** "
               f"({kl['delay_rate']:.1f}%) dibanding bulan biasa ({kb['delay_rate']:.1f}%), selisih "
               f"{kb['delay_rate'] - kl['delay_rate']:.1f} poin. Kemungkinan karena maskapai menambah slot "
               "jadwal dan armada cadangan menjelang liburan.")
    else:
        narasi(f"Sesuai dugaan awal (H3), musim liburan memang **lebih rawan delay** ({kl['delay_rate']:.1f}%) "
               f"dibanding bulan biasa ({kb['delay_rate']:.1f}%), selisih "
               f"{kl['delay_rate'] - kb['delay_rate']:.1f} poin.")


# =====================================================================
# HALAMAN: TENTANG DATA & METODOLOGI
# =====================================================================
def halaman_tentang():
    hero("Tentang Dataset", "Sumber, definisi, dan keterbatasan analisis")
    st.markdown("""
### Sumber Data
- **Airline On-Time Performance** -- U.S. Bureau of Transportation Statistics (BTS), data bulanan Januari 2024-Desember 2025.
- **T-100 Domestic Segment** -- BTS, data tahunan 2024-2025 (volume penerbangan, penumpang, kapasitas kursi per rute).
- **Koordinat bandara** -- [OpenFlights](https://openflights.org/data.html).

### Definisi Utama
- **Delay**: penerbangan dianggap *delay* jika tiba lebih dari **15 menit** dari jadwal, mengikuti standar BTS/FAA.
- **Load factor**: persentase kursi terisi (total penumpang dibagi total kursi tersedia).
- **Rata-rata berbobot**: semua rata-rata delay dihitung berbobot jumlah penerbangan tiap kelompok, bukan rata-rata sederhana antarbaris, karena data sudah berbentuk agregat per rute-bulan-maskapai.

### Keterbatasan
- Data mencakup penerbangan **domestik** AS saja.
- Rincian penyebab delay hanya dicatat BTS untuk penerbangan yang terlambat minimal 15 menit.
- Peringkat maskapai per rute mengecualikan kombinasi dengan kurang dari 30 penerbangan.
- Sekitar 0,2% baris tidak memiliki koordinat bandara yang cocok di OpenFlights, sehingga tidak muncul di peta.

### Kelompok 7
*(Nadia Maretta Rafa, Nabila Dwitya Agustin, Carlene Jean Suzzanna Gaitian, Muhamad Yunus)*
""")

# =====================================================================
# MAIN
# =====================================================================
df = load_data()

st.sidebar.title("Menu Dashboard")
PILIHAN_MENU = ["Beranda", "Ringkasan Delay", "Penyebab Dominan Delay", "Bandara & Bulan Tersibuk",
                "Cek Rute (A ke B)", "Musim Libur (Nov-Des)", "Tentang Dataset"]
_default_menu = st.session_state.get('menu_aktif', "Beranda")
menu = st.sidebar.radio("Pilih Analisis:", PILIHAN_MENU,
                        index=PILIHAN_MENU.index(_default_menu) if _default_menu in PILIHAN_MENU else 0)
st.session_state['menu_aktif'] = menu
st.sidebar.markdown("---")
st.sidebar.subheader("Filter")
semua_tahun = sorted(df['YEAR'].unique())
tahun_pilihan = st.sidebar.multiselect("Tahun:", options=semua_tahun, default=semua_tahun)

df_filtered = df[df['YEAR'].isin(tahun_pilihan)]
if df_filtered.empty:
    st.warning("Pilih minimal satu tahun pada filter di sidebar.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"Periode data: {teks_periode(tahun_pilihan)}  \n"
                   "Sumber: U.S. Bureau of Transportation Statistics (On-Time Performance & T-100 Domestic "
                   "Segment). Koordinat bandara: OpenFlights.")

if menu == "Beranda":
    halaman_beranda(df_filtered)
elif menu == "Ringkasan Delay":
    halaman_ringkasan(df_filtered)
elif menu == "Penyebab Dominan Delay":
    halaman_penyebab(df_filtered)
elif menu == "Bandara & Bulan Tersibuk":
    halaman_tersibuk(df_filtered)
elif menu == "Cek Rute (A ke B)":
    halaman_rute(df_filtered)
elif menu == "Musim Libur (Nov-Des)":
    halaman_musim(df_filtered)
elif menu == "Tentang Dataset":
    halaman_tentang()
