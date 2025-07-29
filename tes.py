from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

def strukturkan_data():
    df = pd.read_csv("monevunsud.csv")

    # Pisah kode
    df['program'] = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+)')
    df['kegiatan'] = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+\.\d{4})')
    df['kro'] = df['KODE'].str.extract(r'^(\d{4}\.\w{3})')
    df['ro'] = df['KODE'].str.extract(r'^(\d{4}\.\w{3}\.\d{3})')
    df['komponen'] = df['KODE'].str.extract(r'^(\d{4}\.\w{3}\.\d{3}\.\d{3})')
    df['sub_komponen'] = df['KODE'].str.extract(r'^(\d{4}\.\w{3}\.\d{3}\.\d{3}\.\w{2})')

    df_pagu = df[df['KET'] == 'PAGU'].copy()
    df_realisasi = df[df['KET'] == 'REALISASI'].copy()

    # Gabungkan Pagu dan Realisasi
    df_agg = df_pagu.merge(
        df_realisasi[['KODE', 'JUMLAH']],
        on='KODE', how='left',
        suffixes=('_pagu', '_realisasi')
    )

    # Bangun struktur nested dictionary
    structured = {}
    for _, row in df_agg.iterrows():
        prog = structured.setdefault(row['program'], {'nama': '', 'pagu': 0, 'realisasi': 0, 'kegiatan': {}})
        prog['pagu'] += row['JUMLAH_pagu']
        prog['realisasi'] += row['JUMLAH_realisasi'] or 0
        prog['nama'] = row['PROGRAM']

        keg = prog['kegiatan'].setdefault(row['kegiatan'], {'nama': row['KEGIATAN'], 'kro': {}})
        kro = keg['kro'].setdefault(row['kro'], {'nama': row['KRO'], 'ro': {}})
        ro = kro['ro'].setdefault(row['ro'], {'nama': row['RO'], 'komponen': {}})
        kom = ro['komponen'].setdefault(row['komponen'], {'nama': row['KOMPONEN'], 'sub_komponen': []})
        kom['sub_komponen'].append({
            'kode': row['sub_komponen'],
            'nama': row['URAIAN'],
            'pagu': row['JUMLAH_pagu'],
            'realisasi': row['JUMLAH_realisasi'] or 0
        })

    return structured

@app.route("/")
def index():
    data = strukturkan_data()
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
