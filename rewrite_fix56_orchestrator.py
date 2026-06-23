from pathlib import Path
import re

path = Path(r'C:\MT5_scripts\FIX56_orchestrator.py')
text = path.read_text(encoding='utf-8-sig')

new_base = r'''BASE_PROFILE = r"""
TestMode=4||4||1||4||N
Seed={seed_value}||{seed_start}||1||{seed_stop}||Y
Debug=false||false||0||true||N
ReverseCoreSignals=false||false||0||true||N
Lots=0.1||0.1||0.010000||1.000000||N
UsePctOfEquity=false||false||0||true||N
RiskPctEquity=1.0||1.0||0.100000||10.000000||N

LTH_OPT_WriteCsv=true||false||0||true||N
LTH_OPT_CsvFile={opt_csv_prefix}.csv
LTH_OPT_RunName={run_name}
LTH_OPT_Suite=FIX56_CORE_ENTRY_RANDOM_EXIT_BENCHMARK

TimesAreET=true||false||0||true||N
StartHHMM=1800||1800||1||1800||N
EndHHMM=700||700||1||700||N
LastEntryHHMM=100||100||1||100||N
Nb={nb}||9||5||19||Y
NATR={natr}||73||10||93||Y
ATRmult={atrmult:.6f}||2.550000||0.300000||3.150000||Y
OneTradePerDay=true||false||0||true||N

UseSessionEndExit=true||false||0||true||N
MaxBarsHeld=0||0||1||0||N
TRmult=0.910000||0.910000||0.010000||0.910000||N
UseBrokerStopsTargets=true||false||0||true||N
Stop_UseUSD=true||false||0||true||N
Stop_USD=150.00||150.00||1.00||150.00||N
Stop_Points=500.00||500.00||1.00||500.00||N

AvgBarsToExit={avg_bars}||{avg_bars}||1||{avg_bars}||N
MinBarsBeforeRandomExit=0||0||1||0||N
TimeExitPolicy=0||0||1||0||N
EOD_ExitHour=23||23||1||23||N
EOD_ExitMinute=0||0||1||0||N
EOW_FridayExitHour=21||21||1||21||N
EOW_FridayExitMinute=0||0||1||0||N

Mode1Policy=2||0||0||3||N
FixedSL_Points=500||500||50||5000||N
FixedTP_Points=500||500||50||5000||N
Mode1_SL_Money=100.0||100.0||10.000000||1000.000000||N
Mode1_TP_Money=100.0||100.0||10.000000||1000.000000||N
Mode1_SL_USD=100.0||100.0||10.000000||1000.000000||N
Mode1_TP_USD=100.0||100.0||10.000000||1000.000000||N
Mode1_ATR_Period=14||14||1||140||N
Mode1_SL_ATR_Mult=2.0||2.0||0.100000||10.000000||N
Mode1_TP_ATR_Mult=2.0||2.0||0.100000||10.000000||N
ExitAfterNBars=3||3||1||3||N

Magic=123456||123456||1||999999||N
MaxSlippagePoints=0||0||1||50||N
UseEntryLimitOrders=false||false||0||true||N
LimitOneBarOnly=true||false||0||true||N

; Keep optimisation fast/clean. We use OnTester CSV shards, not trade traces.
LTH_TRACE_WriteCsv=false||false||0||true||N
LTH_TRACE_ClearCsvOnInit=true||false||0||true||N
LTH_TRACE_Debug=false||false||0||true||N
LTH_TRACE_AutoDisableInOptimization=true||false||0||true||N
LTH_TRACE_File=LTH_trace_FIX56_unused.csv
"""'''

new_build = r'''def build_jobs():
    jobs = []
    avg_bars_values = [2, 3, 4, 5, 6, 8]
    seed_chunks = [(1, 5), (6, 10)]
    idx = 1
    for avg_bars in avg_bars_values:
        for seed_start, seed_stop in seed_chunks:
            run_name = f"FIX56_CORE_RANDOM_EXIT_AB{avg_bars:02d}_S{seed_start:03d}_{seed_stop:03d}"
            job = {
                "idx": idx,
                "name": run_name,
                "avg_bars": avg_bars,
                "nb": 9,
                "natr": 73,
                "atrmult": 2.55,
                "expected": 135,
                "seed_value": seed_start,
                "seed_start": seed_start,
                "seed_stop": seed_stop,
            }
            job["prefix"] = "LTH_opt_" + run_name
            jobs.append(job)
            idx += 1
    return jobs
'''

new_tail = r'''    # Merge all shards collected.
    collected = out_root / "common_files_collected"
    rows = []
    if collected.exists():
        for f in sorted(collected.glob("LTH_opt_FIX56_CORE_RANDOM_EXIT_*.csv")):
            row = read_csv_semicolon(f)
            if not row:
                continue
            row["Nb"] = row.get("Nb", "")
            row["NATR"] = row.get("NATR", "")
            row["ATRmult"] = row.get("ATRmult", "")
            row["AvgBarsToExit"] = row.get("AvgBarsToExit", "")
            row["Seed"] = row.get("Seed", "")
            rows.append(row)

    norm = []
    for r in rows:
        net = safe_float(r.get("net_profit"))
        avg = safe_float(r.get("expected_payoff"))
        pf = safe_float(r.get("profit_factor"))
        tr = safe_int(r.get("trades"))
        favorable = (net > 0 and avg > 0 and pf > 1.0 and tr >= 20)
        norm.append({
            "run_name": r.get("run_name"),
            "suite": r.get("suite"),
            "symbol": r.get("symbol"),
            "period_sec": r.get("period_sec"),
            "test_mode": r.get("test_mode"),
            "entry_index": r.get("entry_index"),
            "entry_title": r.get("entry_title"),
            "entry_file": r.get("entry_file"),
            "entry_signature": r.get("entry_signature"),
            "generic_index": r.get("generic_index"),
            "generic_title": r.get("generic_title"),
            "generic_file": r.get("generic_file"),
            "generic_signature": r.get("generic_signature"),
            "exit_index": r.get("exit_index"),
            "exit_title": r.get("exit_title"),
            "exit_file": r.get("exit_file"),
            "exit_signature": r.get("exit_signature"),
            "net_profit": net,
            "gross_profit": safe_float(r.get("gross_profit")),
            "gross_loss": safe_float(r.get("gross_loss")),
            "profit_factor": pf,
            "expected_payoff": avg,
            "trades": tr,
            "profit_trades": safe_float(r.get("profit_trades")),
            "loss_trades": safe_float(r.get("loss_trades")),
            "win_rate": safe_float(r.get("win_rate")),
            "equity_dd": safe_float(r.get("equity_dd")),
            "equity_dd_rel_pct": safe_float(r.get("equity_dd_rel_pct")),
            "balance_dd": safe_float(r.get("balance_dd")),
            "balance_dd_rel_pct": safe_float(r.get("balance_dd_rel_pct")),
            "Mode1_ATR_Period": row.get("Mode1_ATR_Period"),
            "Mode1_SL_ATR_Mult": row.get("Mode1_SL_ATR_Mult"),
            "Mode1_TP_ATR_Mult": row.get("Mode1_TP_ATR_Mult"),
            "ExitAfterNBars": row.get("ExitAfterNBars"),
            "Seed": row.get("Seed"),
            "AvgBarsToExit": row.get("AvgBarsToExit"),
            "MinBarsBeforeRandomExit": row.get("MinBarsBeforeRandomExit"),
            "TimeExitPolicy": row.get("TimeExitPolicy"),
            "EOD_ExitHour": row.get("EOD_ExitHour"),
            "EOD_ExitMinute": row.get("EOD_ExitMinute"),
            "Lots": row.get("Lots"),
            "MaxSlippagePoints": row.get("MaxSlippagePoints"),
            "Nb": row.get("Nb"),
            "NATR": row.get("NATR"),
            "ATRmult": row.get("ATRmult"),
            "favorable": favorable,
            "source_file": row.get("_source_file"),
        })

    write_csv(out_root / "FIX56_run_status.csv",
              ["idx", "run_name", "expected_passes", "shard_count", "success", "report_ok", "terminal_returncode", "profile", "ini", "report", "prefix"],
              run_status)

    fields = ["run_name", "suite", "symbol", "period_sec", "test_mode", "entry_index", "entry_title", "entry_file", "entry_signature", "generic_index", "generic_title", "generic_file", "generic_signature", "exit_index", "exit_title", "exit_file", "exit_signature", "net_profit", "gross_profit", "gross_loss", "profit_factor", "expected_payoff", "trades", "profit_trades", "loss_trades", "win_rate", "equity_dd", "equity_dd_rel_pct", "balance_dd", "balance_dd_rel_pct", "Mode1_ATR_Period", "Mode1_SL_ATR_Mult", "Mode1_TP_ATR_Mult", "ExitAfterNBars", "Seed", "AvgBarsToExit", "MinBarsBeforeRandomExit", "TimeExitPolicy", "EOD_ExitHour", "EOD_ExitMinute", "Lots", "MaxSlippagePoints", "Nb", "NATR", "ATRmult", "favorable", "source_file"]
    write_csv(out_root / "FIX56_CORE_RANDOM_EXIT_merged_summary.csv", fields, norm)

    def aggregate(keys, out_name):
        agg = {}
        for r in norm:
            key = tuple(str(r.get(k, "")) for k in keys)
            a = agg.setdefault(key, {k: r.get(k, "") for k in keys} | {"rows": 0, "favorable_rows": 0, "net_profit_sum": 0.0, "expected_payoff_sum": 0.0, "profit_factor_sum": 0.0, "trades_sum": 0})
            a["rows"] += 1
            a["favorable_rows"] += 1 if r.get("favorable") else 0
            a["net_profit_sum"] += safe_float(r.get("net_profit"))
            a["expected_payoff_sum"] += safe_float(r.get("expected_payoff"))
            a["profit_factor_sum"] += safe_float(r.get("profit_factor"))
            a["trades_sum"] += safe_int(r.get("trades"))
        rows_out = []
        for a in agg.values():
            n = max(1, a["rows"])
            rows_out.append({
                **a,
                "favorable_pct": 100.0 * a["favorable_rows"] / n,
                "net_profit_avg": a["net_profit_sum"] / n,
                "expected_payoff_avg": a["expected_payoff_sum"] / n,
                "profit_factor_avg": a["profit_factor_sum"] / n,
                "trades_avg": a["trades_sum"] / n,
            })
        write_csv(out_root / out_name,
                  keys + ["rows", "favorable_rows", "favorable_pct", "net_profit_sum", "net_profit_avg", "expected_payoff_avg", "profit_factor_avg", "trades_avg"],
                  sorted(rows_out, key=lambda x: tuple(str(x.get(k, "")) for k in keys)))

    aggregate(["AvgBarsToExit"], "FIX56_CORE_RANDOM_EXIT_by_AvgBarsToExit.csv")
    aggregate(["Nb", "NATR", "ATRmult", "AvgBarsToExit"], "FIX56_CORE_RANDOM_EXIT_grid.csv")
    aggregate(["Nb", "NATR", "ATRmult"], "FIX56_CORE_RANDOM_EXIT_by_entry_params.csv")
    aggregate(["Seed"], "FIX56_CORE_RANDOM_EXIT_by_seed.csv")

    all_ok = bool(run_status) and len(run_status) == len(jobs) and all(bool(x["success"]) for x in run_status)
    log("")
    log(f"FIX56 jobs_completed={len(run_status)}/{len(jobs)} all_jobs_success={all_ok}")
    log(f"merged_rows={len(norm)} expected_total_passes=1620")
    log(f"output_folder={out_root}")
    log("Upload the full LTH_limited_results_FIX56_CORE_RANDOM_EXIT_BENCHMARK_OPT_* folder/zip.")
    if not all_ok:
        sys.exit(10)
    if len(norm) < 1620:
        sys.exit(11)


if __name__ == "__main__":
    main()
'''

text2 = re.sub(r'BASE_PROFILE = r"""[\s\S]*?"""', new_base, text, count=1)
text2 = re.sub(r'def build_jobs\(\):[\s\S]*?return jobs\n', new_build + '\n', text2, count=1)
text2 = re.sub(r'    # Merge all shards collected\.[\s\S]*?if __name__ == "__main__":\n    main\(\)\n', new_tail + '\n', text2, count=1)
text2 = text2.replace('FIX54', 'FIX56')
text2 = text2.replace('RANDOM_ENTRY_EXIT', 'CORE_RANDOM_EXIT')
text2 = text2.replace('random entry + EuroNight exit', 'core random-exit benchmark')
text2 = text2.replace('EURONIGHT', 'EURONIGHT')
text2 = text2.replace('LTH_opt_FIX56_CORE_RANDOM_EXIT_AB', 'LTH_opt_FIX56_CORE_RANDOM_EXIT_AB')
path.write_text(text2, encoding='utf-8-sig', newline='\r\n')
print(path)
