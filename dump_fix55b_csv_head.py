import zipfile
ZIP=r'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
with zipfile.ZipFile(ZIP) as z:
    csvs=[n for n in z.namelist() if '/common_files_collected/' in n and n.lower().endswith('.csv')]
    print('CSV COUNT', len(csvs))
    s=csvs[0]
    print('\n###', s)
    txt=z.read(s).decode('utf-8-sig', errors='replace')
    print(txt[:4000])
