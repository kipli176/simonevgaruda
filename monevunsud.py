from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

@app.route('/')
def dashboard():
    df = pd.read_csv('monevunsud.csv')

    # Standarisasi kolom
    df.columns = df.columns.str.upper().str.strip().str.replace(' ', '_')
    df['JUMLAH'] = pd.to_numeric(df['JUMLAH'], errors='coerce').fillna(0)
    df['KET'] = df['KET'].str.upper()
    # --- filter unit jika parameter ada ---

    # siapkan list unit untuk dropdown
    units = sorted(df['UNIT'].unique()) 
    # ambil filter unit
    selected_unit = request.args.get('unit')
    if selected_unit:
        df = df[df['UNIT'] == selected_unit]

    # Agregasi per Unit
    # hitung pagu per unit
    pagu_unit = (
        df[df.KET == 'PAGU']
        .groupby('UNIT', as_index=False)['JUMLAH']
        .sum()
        .rename(columns={'JUMLAH': 'pagu'})
    )

    # hitung realisasi per unit
    real_unit = (
        df[df.KET == 'REALISASI']
        .groupby('UNIT', as_index=False)['JUMLAH']
        .sum()
        .rename(columns={'JUMLAH': 'realisasi'})
    )

    # gabung kedua hasilnya
    agg_unit = (
        pagu_unit
        .merge(real_unit, on='UNIT', how='outer')
        .fillna(0)
    )
    units_summary = [
        (row.UNIT, row.pagu, row.realisasi)
        for _, row in agg_unit.iterrows()
    ]

    # Jika filter unit dipakai, agregasi per Subunit
    if selected_unit:
        # Ganti 'SUBUNIT' dengan nama kolom sub‐unit yang sesuai
        pagu_sub = (
            df[df.KET == 'PAGU']
            .groupby('SUBUNIT', as_index=False)['JUMLAH']
            .sum()
            .rename(columns={'JUMLAH': 'pagu'})
        )
        real_sub = (
            df[df.KET == 'REALISASI']
            .groupby('SUBUNIT', as_index=False)['JUMLAH']
            .sum()
            .rename(columns={'JUMLAH': 'realisasi'})
        )
        agg_sub = pagu_sub.merge(real_sub, on='SUBUNIT', how='outer').fillna(0)

        subunits_summary = [
            (row.SUBUNIT, row.pagu, row.realisasi)
            for _, row in agg_sub.iterrows()
        ]
    else:
        subunits_summary = []

    # ===============================
    # 1. REALISASI PER JENIS BELANJA
    # ===============================
    jenis_belanja = []
    total_pagu_jb, total_real_jb = 0, 0
    for i, jenis in enumerate(df['JENIS_BELANJA'].dropna().unique(), 1):
        pagu = df[(df['JENIS_BELANJA'] == jenis) & (df['KET'] == 'PAGU')]['JUMLAH'].sum()
        real = df[(df['JENIS_BELANJA'] == jenis) & (df['KET'] == 'REALISASI')]['JUMLAH'].sum()
        persen = (real / pagu * 100) if pagu > 0 else 0
        total_pagu_jb += pagu
        total_real_jb += real
        jenis_belanja.append({'NO': i, 'JENIS_BELANJA': jenis, 'PAGU': pagu, 'REALISASI': real, 'PERSEN': persen})
    total_jenis_belanja = {
        'pagu': total_pagu_jb,
        'realisasi': total_real_jb,
        'persen': (total_real_jb / total_pagu_jb * 100) if total_pagu_jb > 0 else 0
    }

    # ===============================
    # 2. REALISASI PER SUMBER DANA
    # ===============================
    sumber_dana = []
    total_pagu_sd, total_real_sd = 0, 0
    for i, sumber in enumerate(df['SUMBER_DANA'].dropna().unique(), 1):
        pagu = df[(df['SUMBER_DANA'] == sumber) & (df['KET'] == 'PAGU')]['JUMLAH'].sum()
        real = df[(df['SUMBER_DANA'] == sumber) & (df['KET'] == 'REALISASI')]['JUMLAH'].sum()
        persen = (real / pagu * 100) if pagu > 0 else 0
        total_pagu_sd += pagu
        total_real_sd += real
        sumber_dana.append({'NO': i, 'SUMBER_DANA': sumber, 'PAGU': pagu, 'REALISASI': real, 'PERSEN': persen})
    total_sumber_dana = {
        'pagu': total_pagu_sd,
        'realisasi': total_real_sd,
        'persen': (total_real_sd / total_pagu_sd * 100) if total_pagu_sd > 0 else 0
    } 

    # ===============================
    # 3. REALISASI PER PROGRAM - KEGIATAN - KRO - RO
    # ===============================
    df['PROGRAM_CODE'] = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+)')
    df['KEGIATAN_CODE'] = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+\.\d{4})')
    df['KRO_CODE'] = df['KODE'].apply(lambda x: '.'.join(x.split('.')[:5]) if isinstance(x, str) else None)
    df['RO_CODE'] = df['KODE'].apply(lambda x: '.'.join(x.split('.')[:6]) if isinstance(x, str) else None)


    # print(df[['KODE', 'PROGRAM', 'KEGIATAN', 'KRO', 'RO']].drop_duplicates().head(10))
    rows = []
    total_pagu = 0
    total_realisasi = 0
    no = 1

    def add_row(level, nama, pagu, realisasi, kode=None):
        nonlocal no, total_pagu, total_realisasi
        persen = (realisasi / pagu * 100) if pagu > 0 else 0
        row = {
            'NO': no,
            'LEVEL': level,
            'NAMA': nama,
            'PAGU': pagu,
            'REALISASI': realisasi,
            'PERSEN': persen,
            'KODE': kode  # untuk tombol detail
        }
        no += 1
        total_pagu += pagu
        total_realisasi += realisasi
        rows.append(row)

    # Urutkan program seperti biasa
    for program_code in sorted(df['PROGRAM_CODE'].dropna().unique()):
        df_prog = df[df['PROGRAM_CODE'] == program_code]
        nama_prog = df_prog.iloc[0]['PROGRAM']

        add_row('PROGRAM', f"[{program_code}] {nama_prog}",
                df_prog[df_prog['KET'] == 'PAGU']['JUMLAH'].sum(),
                df_prog[df_prog['KET'] == 'REALISASI']['JUMLAH'].sum())

        # Urutkan kegiatan berdasarkan 4 digit terakhir
        kegiatan_sorted = (
            df_prog[['KEGIATAN_CODE', 'KEGIATAN']].drop_duplicates()
            .assign(SORTKEY=lambda d: d['KEGIATAN_CODE'].str.extract(r'\.(\d{4})$')[0].astype(int))
            .sort_values('SORTKEY')
        )

        for _, keg_row in kegiatan_sorted.iterrows():
            kegiatan_code = keg_row['KEGIATAN_CODE']
            nama_keg = keg_row['KEGIATAN']
            df_keg = df_prog[df_prog['KEGIATAN_CODE'] == kegiatan_code]

            add_row('KEGIATAN', f"[{kegiatan_code}] {nama_keg}",
                    df_keg[df_keg['KET'] == 'PAGU']['JUMLAH'].sum(),
                    df_keg[df_keg['KET'] == 'REALISASI']['JUMLAH'].sum())

            for kro_code in sorted(df_keg['KRO_CODE'].dropna().unique()):
                df_kro = df_keg[df_keg['KRO_CODE'] == kro_code]
                nama_kro = df_kro.iloc[0]['KRO']

                add_row('KRO', f"[{kro_code}] {nama_kro}",
                        df_kro[df_kro['KET'] == 'PAGU']['JUMLAH'].sum(),
                        df_kro[df_kro['KET'] == 'REALISASI']['JUMLAH'].sum())

                # Urutkan RO berdasarkan angka akhir
                df_ro_unique = (
                    df_kro[['RO_CODE', 'RO']].dropna().drop_duplicates()
                    .assign(RO_SORT=lambda d: d['RO_CODE'].str.extract(r'(\d{3})$')[0].astype(int))
                    .sort_values('RO_SORT')
                )

                for _, ro_row in df_ro_unique.iterrows():
                    ro_code = ro_row['RO_CODE']
                    nama_ro = ro_row['RO']
                    df_ro = df_kro[df_kro['RO_CODE'] == ro_code]

                    add_row('RO', f"[{ro_code}] {nama_ro}",
                            df_ro[df_ro['KET'] == 'PAGU']['JUMLAH'].sum(),
                            df_ro[df_ro['KET'] == 'REALISASI']['JUMLAH'].sum(),
                            kode=ro_code)






    df_program = pd.DataFrame(rows)
    df_program_only = df_program[df_program['LEVEL'] == 'PROGRAM']

    total_program_kegiatan = {
        'pagu': df_program_only['PAGU'].sum(),
        'realisasi': df_program_only['REALISASI'].sum(),
        'persen': df_program_only['REALISASI'].sum() / df_program_only['PAGU'].sum() * 100
    }

  # =============== Widget Realisasi Belanja ===============

    # Lebih aman: anggap semua PENGELUARAN kecuali PENDAPATAN
    # atau sesuaikan berdasarkan struktur jika kamu punya kode PENDAPATAN
    belanja_df = df[df['KET'].isin(['PAGU', 'REALISASI'])]
    belanja_df = belanja_df[~belanja_df['URAIAN'].str.contains("Pendapatan", case=False, na=False)]

    # Total Pagu dan Realisasi
    belanja_pagu = belanja_df[belanja_df['KET'] == 'PAGU']['JUMLAH'].sum()
    belanja_realisasi = belanja_df[belanja_df['KET'] == 'REALISASI']['JUMLAH'].sum()

    # Persentase realisasi
    belanja_persen = (belanja_realisasi / belanja_pagu * 100) if belanja_pagu else 0

    widget_belanja = {
        'pagu': belanja_pagu,
        'realisasi': belanja_realisasi,
        'persen': belanja_persen
    }

    # =============== Widget Realisasi Tertinggi ===============

    # Realisasi berdasarkan URAIAN (bukan pendapatan)
    realisasi_only = df[df['KET'] == 'REALISASI']
    realisasi_only = realisasi_only[~realisasi_only['URAIAN'].str.contains("Pendapatan", case=False, na=False)]

    top_realisasi_uraian = (
        realisasi_only
        .groupby('URAIAN')['JUMLAH']
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )

    top_uraian_nama = top_realisasi_uraian.index[0]
    top_uraian_nilai = top_realisasi_uraian.iloc[0]


    # Widget 3: Jumlah Program dan Kegiatan
    jumlah_program = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+)')[0].nunique()
    jumlah_kegiatan = df['KODE'].str.extract(r'^(\d+\.\d+\.\w+\.\d{4})')[0].nunique()

    widget_summary = {
        'program': jumlah_program,
        'kegiatan': jumlah_kegiatan
    }
    chart_belanja = {
        'labels': [str(row['JENIS_BELANJA']) for row in jenis_belanja],
        'pagu': [int(row['PAGU']) for row in jenis_belanja],
        'realisasi': [int(row['REALISASI']) for row in jenis_belanja],
        'persen': [float(row['PERSEN']) for row in jenis_belanja]
    }



    return render_template(
        'monevunsud.html',
        units=units,
        selected_unit=selected_unit, 
        units_summary=units_summary,
        subunits_summary=subunits_summary,
        jenis_belanja=jenis_belanja,
        sumber_dana=sumber_dana,
        total_jenis_belanja=total_jenis_belanja,
        total_sumber_dana=total_sumber_dana,
        program_kegiatan=rows,
        total_program_kegiatan=total_program_kegiatan,
        widget_belanja=widget_belanja,
        widget_summary=widget_summary,
        top_uraian_nama=top_uraian_nama,
        top_uraian_nilai=top_uraian_nilai,
        chart_belanja=chart_belanja

    )

def pecah_kode(kode_str):
    parts = kode_str.split('.')
    return {
        'nama_prog': parts[2] if len(parts) > 2 else '',
        'nama_keg': '.'.join(parts[2:4]) if len(parts) > 3 else '',
        'nama_kro': '.'.join(parts[3:5]) if len(parts) > 4 else '',
        'nama_ro': '.'.join(parts[3:6]) if len(parts) > 5 else '',
    }


from flask import jsonify, render_template
import os
@app.route('/detail_ro/<kode>')
def detail_ro(kode):
    # 1. Baca & preprocess CSV
    csv_path = os.path.join(app.root_path, 'monevunsud.csv')
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.upper().str.strip()
    df['JUMLAH'] = pd.to_numeric(df['JUMLAH'], errors='coerce').fillna(0)
    df['KET']     = df['KET'].str.upper()
    df['KODE']    = df['KODE'].astype(str)

    # 2. Ekstraksi struktur kode
    df['RO_CODE']            = df['KODE'].apply(lambda x: '.'.join(x.split('.')[:6]))
    df['KOMPONEN_CODE']      = df['KODE'].apply(lambda x: '.'.join(x.split('.')[:7]))
    df['SUB_KOMPONEN_CODE']  = df['KODE'].apply(lambda x: '.'.join(x.split('.')[:8]))

    # 3. Filter berdasarkan RO
    df_ro = df[df['RO_CODE'] == kode]
    if df_ro.empty:
        return render_template(
            'detail_ro.html',
            error=f"Tidak ada data ditemukan untuk kode RO: {kode}"
        )

    # 4. Info ringkas RO
    ro_uraian   = df_ro.iloc[0].get('RO', kode)
    ro_pagu     = df_ro.loc[df_ro['KET']=='PAGU', 'JUMLAH'].sum()
    ro_real     = df_ro.loc[df_ro['KET']=='REALISASI', 'JUMLAH'].sum()
    ro_persen   = (ro_real/ro_pagu*100) if ro_pagu else 0
    ro_info = {
        'kode':      kode,
        'uraian':    ro_uraian,
        'pagu':      ro_pagu,
        'realisasi': ro_real,
        'persen':    ro_persen
    }

    # 5. Agregasi PAGU & REALISASI per Komponen/Sub‑komponen
    df_pagu = (
        df_ro[df_ro['KET']=='PAGU']
        .groupby(
            ['KOMPONEN_CODE','KOMPONEN',
             'SUB_KOMPONEN_CODE','SUBKOMPONEN']
        )['JUMLAH']
        .sum()
        .reset_index(name='PAGU')
    )
    df_real = (
        df_ro[df_ro['KET']=='REALISASI']
        .groupby(
            ['KOMPONEN_CODE','KOMPONEN',
             'SUB_KOMPONEN_CODE','SUBKOMPONEN']
        )['JUMLAH']
        .sum()
        .reset_index(name='REALISASI')
    )

    # 6. Merge & hitung persen
    df_detail = pd.merge(
        df_pagu, df_real,
        on=['KOMPONEN_CODE','KOMPONEN',
            'SUB_KOMPONEN_CODE','SUBKOMPONEN'],
        how='outer'
    ).fillna(0)
    df_detail['PERSEN'] = df_detail.apply(
        lambda r: (r.REALISASI / r.PAGU * 100) if r.PAGU>0 else 0,
        axis=1
    )

    # 7. Bangun struktur nested untuk template
    grouped = []
    for (komp_code, komp_nama), comp_df in df_detail.groupby(
            ['KOMPONEN_CODE','KOMPONEN'], sort=False):

        # kumpulkan sub‑komponen
        sub_rows = [{
            'kode':      row.SUB_KOMPONEN_CODE,
            'uraian':    row.SUBKOMPONEN,
            'pagu':      row.PAGU,
            'realisasi': row.REALISASI,
            'persen':    row.PERSEN
        } for row in comp_df.itertuples()]

        # total tiap komponen
        total_pagu  = comp_df['PAGU'].sum()
        total_real  = comp_df['REALISASI'].sum()
        total_per   = (total_real / total_pagu * 100) if total_pagu else 0

        grouped.append({
            'kode':      komp_code,
            'uraian':    komp_nama,
            'pagu':      total_pagu,
            'realisasi': total_real,
            'persen':    total_per,
            'sub':       sub_rows
        })

    # 8. Hitung grand total
    grand_pagu   = df_detail['PAGU'].sum()
    grand_real   = df_detail['REALISASI'].sum()
    grand_persen = (grand_real / grand_pagu * 100) if grand_pagu else 0

    return render_template(
        'detail_ro.html',
        ro=ro_info,
        grouped=grouped,
        grand_pagu=grand_pagu,
        grand_real=grand_real,
        grand_persen=grand_persen
    )

if __name__ == '__main__':
    app.run(debug=True)
