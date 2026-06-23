import zipfile
ZIP=r'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
with zipfile.ZipFile(ZIP) as z:
    log=[n for n in z.namelist() if n.endswith('runner_FIX55B_core_random_exit_benchmark.log')][0]
    data=z.read(log).decode('utf-8-sig',errors='replace').splitlines()
    for i,line in enumerate(data[:260],1):
        print(f'{i:04d}: {line}')
