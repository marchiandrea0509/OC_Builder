import zipfile
ZIP=r'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
with zipfile.ZipFile(ZIP) as z:
    sets=[n for n in z.namelist() if n.lower().endswith('.set')]
    print('SET COUNT', len(sets))
    for s in sets[:3]:
        print('\n###', s)
        txt=z.read(s).decode('utf-16', errors='replace')
        print(txt[:4000])
