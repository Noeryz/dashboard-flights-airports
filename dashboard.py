import html
import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Ketepatan Waktu Penerbangan AS",
                   page_icon="✈️", layout="wide")

# =====================================================================
# KONSTANTA & TEMA HIJAU
# =====================================================================
FILE_DATA = "Data_Dashboard_Final.parquet"
FILE_KOORDINAT = "airports_coords.csv"
URUTAN_BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
MIN_PENERBANGAN = 30

HIJAU_TUA, HIJAU, HIJAU_MUDA = "#0B5D3B", "#1B8A5A", "#74C69D"
PALET = [HIJAU_TUA, HIJAU_MUDA, HIJAU, "#B7E4C7", "#40916C", "#95D5B2", "#2D6A4F", "#D8F3DC"]
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = PALET
px.defaults.color_continuous_scale = "Greens"

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

CSS_HALAMAN = """
.hero{background:linear-gradient(120deg,#0B5D3B,#1B8A5A 60%,#52B788);color:#fff;padding:26px 32px;
 border-radius:16px;position:relative;overflow:hidden;margin-bottom:18px;animation:fade .8s ease}
.hero h1{margin:0;font-size:2rem;color:#fff;padding:0}
.hero p{margin:6px 0 0;opacity:.92;color:#fff}
.pesawat{position:absolute;top:16px;font-size:34px;animation:terbang 10s linear infinite;opacity:.85}
@keyframes terbang{0%{left:-60px;transform:translateY(0)}50%{transform:translateY(14px)}100%{left:105%;transform:translateY(0)}}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.insight{background:#E4F4EA;border-left:6px solid #1B8A5A;border-radius:10px;padding:14px 18px;margin:8px 0 22px;
 color:#12372A;animation:fade .8s ease;line-height:1.55}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{animation:fade .8s ease}
h2,h3{color:#0B5D3B}
"""

CSS_KARTU = """
body{margin:0;font-family:"Source Sans Pro",Arial,sans-serif}
.row{display:flex;gap:14px}
.k{flex:1;background:#fff;border-left:6px solid #1B8A5A;border-radius:12px;padding:14px 16px;
 box-shadow:0 2px 8px rgba(11,93,59,.15);transition:transform .25s,box-shadow .25s;
 animation:naik .7s ease both}
.k:hover{transform:translateY(-4px);box-shadow:0 8px 18px rgba(11,93,59,.28)}
.t{font-size:13px;color:#3D6B57}
.v{font-size:28px;font-weight:700;color:#0B5D3B;margin-top:4px}
@keyframes naik{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
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
                      font=dict(color="#12372A"), margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, **LEBAR_PENUH)


def atur_animasi(fig, durasi=900):
    """Perlambat animasi supaya perubahan antarbulan terbaca."""
    try:
        args = fig.layout.updatemenus[0].buttons[0].args[1]
        args["frame"]["duration"] = durasi
        args["transition"]["duration"] = durasi // 2
    except Exception:
        pass


def kpi_row(items):
    """items: list (judul, nilai, desimal, akhiran). Nilai angka -> animasi hitung naik;
    nilai teks -> ditampilkan apa adanya."""
    kartu = ""
    for i, (judul, nilai, des, akh) in enumerate(items):
        if isinstance(nilai, str):
            isi = html.escape(nilai)
        elif nilai != nilai:
            isi = "n/a"
        else:
            isi = f'<span class="n" data-v="{nilai}" data-d="{des}">0</span>{akh}'
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
    kpi_row([("Persentase Delay (>15 menit)", kpi['delay_rate'], 1, "%"),
             ("Rata-rata Delay", kpi['avg_delay'], 1, " menit"),
             ("Total Penerbangan", kpi['total_flights'], 0, ""),
             ("Rata-rata Load Factor", kpi['load_factor'], 1, "%")])

    with st.expander("ℹ️ Cara membaca metrik delay"):
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
    per_maskapai = ringkas(data, 'maskapai').sort_values(kolom, ascending=True)
    fig1 = px.bar(per_maskapai, x=kolom, y='maskapai', orientation='h', color=kolom,
                  hover_data={'total_flights': ':,.0f', 'delay_rate': ':.1f', 'avg_delay': ':.1f'},
                  labels={kolom: label, 'maskapai': 'Maskapai', 'total_flights': 'Total penerbangan',
                          'delay_rate': 'Delay (%)', 'avg_delay': 'Rata-rata delay (mnt)'})
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
                   category_orders={'BULAN': URUTAN_BULAN}, labels={kolom: label, 'BULAN': 'Bulan'})
    tampil(fig2)
    tinggi, rendah = per_bulan.loc[per_bulan[kolom].idxmax()], per_bulan.loc[per_bulan[kolom].idxmin()]
    narasi(f"Delay paling parah terjadi pada bulan **{tinggi['BULAN']}** ({fmt_metrik(kolom, tinggi[kolom])}) "
           f"dan paling lancar pada **{rendah['BULAN']}** ({fmt_metrik(kolom, rendah[kolom])}), "
           f"selisih {fmt_selisih(kolom, tinggi[kolom] - rendah[kolom])}. "
           "Lihat menu *Penyebab Dominan Delay* untuk faktor di baliknya.")

    # ----- Grafik 3: animasi bar per bulan -----
    st.subheader("🎬 Animasi: Delay Maskapai Bulan ke Bulan")
    st.caption("Tekan tombol ▶ Play di bawah grafik, atau geser slider bulan.")
    anim = urutkan_bulan(ringkas(data, ['BULAN', 'maskapai']))
    anim['BULAN'] = anim['BULAN'].astype(str)
    fig3 = px.bar(anim, x=kolom, y='maskapai', orientation='h', color=kolom,
                  animation_frame='BULAN', range_x=[0, anim[kolom].max() * 1.15],
                  range_color=[0, anim[kolom].max()],
                  category_orders={'BULAN': bulan_tersedia(data),
                                   'maskapai': per_maskapai['maskapai'].tolist()},
                  labels={kolom: label, 'maskapai': 'Maskapai', 'BULAN': 'Bulan'})
    atur_animasi(fig3)
    tampil(fig3)
    pv = anim.pivot(index='maskapai', columns='BULAN', values=kolom)
    goyang = (pv.max(axis=1) - pv.min(axis=1)).idxmax()
    narasi(f"**{goyang}** paling berubah-ubah sepanjang tahun: terbaik pada bulan **{pv.loc[goyang].idxmin()}** "
           f"({fmt_metrik(kolom, pv.loc[goyang].min())}) dan terburuk pada **{pv.loc[goyang].idxmax()}** "
           f"({fmt_metrik(kolom, pv.loc[goyang].max())}). Urutan maskapai pada grafik tetap, "
           "yang bergerak adalah panjang batangnya.")


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

    fig1 = px.pie(values=total.values, names=total.index, hole=0.45,
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
                  category_orders={'BULAN': URUTAN_BULAN},
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
    bandara = top_bandara(data)
    fig1 = px.bar(bandara.sort_values('total_flights'), x='total_flights', y='bandara', orientation='h',
                  color='total_flights', labels={'total_flights': 'Total Penerbangan', 'bandara': 'Bandara'})
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

    st.subheader("🎬 Animasi: Kepadatan Penerbangan per Bulan")
    st.caption("Tekan ▶ Play untuk melihat titik padat berpindah dari bulan ke bulan.")
    peta = urutkan_bulan(data.groupby(['BULAN', 'ORIGIN', 'origin_lat', 'origin_lon'])['total_flights']
                         .sum().reset_index())
    peta['BULAN'] = peta['BULAN'].astype(str)
    skala = [[0, "rgba(116,198,157,0)"], [0.3, HIJAU_MUDA], [1, HIJAU_TUA]]
    fig_peta = px.density_map(peta, lat='origin_lat', lon='origin_lon', z='total_flights', radius=18,
                              animation_frame='BULAN', category_orders={'BULAN': bulan_tersedia(data)},
                              center=dict(lat=39, lon=-98), zoom=3, map_style="open-street-map",
                              range_color=[0, peta['total_flights'].max()], opacity=0.8,
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
    tampil(fig3)
    tiga = top_b['bandara'].head(3).tolist()
    narasi(f"Pada bulan **{bulan_pilih}**, tiga bandara tersibuk adalah " + ", ".join(f"**{x}**" for x in tiga) + ".")


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
            opacity=1 if sorot else 0.55, hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scattermap(
        lat=jar['dest_lat'], lon=jar['dest_lon'], mode='markers', showlegend=False,
        marker=dict(size=8, color=HIJAU), hoverinfo='text',
        text=jar['dest_label'] + " (" + jar['DEST'] + "): " + jar['total_flights'].map('{:,.0f}'.format) + " penerbangan"))
    fig.add_trace(go.Scattermap(
        lat=[o_lat], lon=[o_lon], mode='markers', showlegend=False, hoverinfo='text',
        marker=dict(size=16, color=HIJAU_TUA), text=f"{asal} ({kode_o}) - kota asal"))
    fig.update_layout(map_style="open-street-map", map_center=dict(lat=39, lon=-98),
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

    daftar_asal = sorted(data['origin_label'].unique())
    c1, c2, c3 = st.columns(3)
    asal = c1.selectbox("Dari Kota:", daftar_asal,
                        index=daftar_asal.index("Atlanta") if "Atlanta" in daftar_asal else 0)
    tujuan = c2.selectbox("Ke Kota:", sorted(data.loc[data['origin_label'] == asal, 'dest_label'].unique()))
    bulan_pilih = c3.selectbox("Bulan (untuk peringkat):", ["Semua bulan"] + bulan_tersedia(data))
    salju_sekali(bulan_pilih)

    rute = data[(data['origin_label'] == asal) & (data['dest_label'] == tujuan)]
    if rute.empty:
        st.warning("Tidak ada data penerbangan untuk rute ini pada tahun yang difilter.")
        return

    kpi = hitung_kpi(rute)
    kpi_row([("Total Penerbangan", kpi['total_flights'], 0, ""),
             ("Persentase Delay (>15 menit)", kpi['delay_rate'], 1, "%"),
             ("Rata-rata Delay", kpi['avg_delay'], 1, " menit"),
             ("Bulan Tersibuk", rute.groupby('BULAN')['total_flights'].sum().idxmax(), 0, "")])

    # ----- Peringkat maskapai -----
    ket = "sepanjang tahun" if bulan_pilih == "Semua bulan" else f"bulan {bulan_pilih}"
    st.subheader(f"🏆 Peringkat Maskapai: {asal} → {tujuan} ({ket})")
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

        st.dataframe(pd.DataFrame({
            'Peringkat': [str(i + 1) if ok else "–" for i, ok in enumerate(rank['cukup'])],
            'Maskapai': rank['maskapai'],
            'Total Penerbangan': rank['total_flights'].map('{:,.0f}'.format),
            '% Delay (>15 mnt)': rank['delay_rate'].map('{:.1f}%'.format),
            'Rata-rata Delay (mnt)': rank['avg_delay'].map('{:.1f}'.format),
            'Load Factor': rank['load_factor'].map(lambda v: f"{v:.1f}%" if pd.notna(v) else "n/a"),
            'Catatan': ["" if ok else "Data terbatas" for ok in rank['cukup']],
        }), hide_index=True)

        rp = rank.iloc[::-1].copy()
        rp['Status'] = rp['cukup'].map({True: 'Data memadai', False: f'Data terbatas (<{MIN_PENERBANGAN})'})
        rp['label'] = rp['delay_rate'].map('{:.1f}%'.format)
        tampil(px.bar(rp, x='delay_rate', y='maskapai', orientation='h', color='Status', text='label',
                      color_discrete_map={'Data memadai': HIJAU, f'Data terbatas (<{MIN_PENERBANGAN})': '#B0B0B0'},
                      labels={'delay_rate': 'Penerbangan delay (%)', 'maskapai': 'Maskapai'}))

        if n_cukup == 0:
            narasi(f"Belum ada maskapai dengan minimal {MIN_PENERBANGAN} penerbangan pada rute dan bulan ini, "
                   "sehingga peringkat yang andal belum bisa dibuat. Coba pilih *Semua bulan* atau aktifkan "
                   "kedua tahun pada filter.")
        else:
            layak = rank[rank['cukup']]
            b = layak.iloc[0]
            teks = (f"Untuk rute {asal} → {tujuan} ({ket}), maskapai paling tepat waktu adalah **{b['maskapai']}** "
                    f"({b['delay_rate']:.1f}% penerbangan delay dari {b['total_flights']:,.0f} penerbangan).")
            if n_cukup >= 2:
                w = layak.iloc[-1]
                teks += (f" Yang paling sering delay adalah **{w['maskapai']}** ({w['delay_rate']:.1f}%), "
                         f"selisih {w['delay_rate'] - b['delay_rate']:.1f} poin persentase.")
                lf = layak.dropna(subset=['load_factor'])
                if not lf.empty:
                    s = lf.sort_values('load_factor').iloc[0]
                    teks += (f" Jika ingin penerbangan yang lebih lengang, **{s['maskapai']}** punya rata-rata "
                             f"load factor terendah ({s['load_factor']:.1f}%).")
            else:
                teks += " Hanya satu maskapai yang memenuhi batas minimal data, jadi belum ada pembanding."
            if n_cukup < len(rank):
                teks += f" Maskapai berlabel abu-abu punya data kurang dari {MIN_PENERBANGAN} penerbangan."
            narasi(teks)

    # ----- Peta jaringan rute -----
    st.subheader("🗺️ Peta Jaringan Rute")
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
# MAIN
# =====================================================================
df = load_data()

st.sidebar.title("📊 Menu Dashboard")
menu = st.sidebar.radio("Pilih Analisis:", ["Ringkasan Delay", "Penyebab Dominan Delay",
                                            "Bandara & Bulan Tersibuk", "Cek Rute (A ke B)"])
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

if menu == "Ringkasan Delay":
    halaman_ringkasan(df_filtered)
elif menu == "Penyebab Dominan Delay":
    halaman_penyebab(df_filtered)
elif menu == "Bandara & Bulan Tersibuk":
    halaman_tersibuk(df_filtered)
elif menu == "Cek Rute (A ke B)":
    halaman_rute(df_filtered)
