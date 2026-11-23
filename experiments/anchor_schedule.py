"""Assignment 06: equal-budget scheduled versus jittered clock measurements.

Synthetic experimental choices; the Assignment 05 threshold stays fixed at 2.
"""
import argparse
import csv
from dataclasses import dataclass, asdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
from statistics import fmean, stdev

from experiments.paired_timing import Observations, score
from experiments.selective_correction import interpolate_clock, selective_correct

THRESHOLD = 2.
JITTER_FRACTION = .3


@dataclass(frozen=True)
class Condition:
    profile: str
    period_s: float
    phase_rad: float
    spacing_s: int
    anchor_sd_ms: float


def clock_value(condition, t):
    if condition.profile == 'none':
        return 0.
    if condition.profile == 'linear':
        return .1*t
    if condition.profile == 'oscillating' and condition.period_s > 0:
        return 20*math.sin(2*math.pi*t/condition.period_s + condition.phase_rad)
    raise ValueError('Unsupported clock profile or period.')


def schedule(spacing, seed, jitter=False):
    if spacing not in (60,150,300,600):
        raise ValueError('Unsupported spacing.')
    times = [float(t) for t in range(0,601,spacing)]
    if jitter:
        rng = random.Random(3000000+seed)
        for i in range(1,len(times)-1):
            times[i] += rng.uniform(-JITTER_FRACTION, JITTER_FRACTION)*spacing
    return tuple(times)


def evaluate(condition, seed):
    if not all(math.isfinite(x) for x in (condition.period_s, condition.phase_rad, condition.anchor_sd_ms)) or condition.anchor_sd_ms < 0:
        raise ValueError('Finite parameters and nonnegative anchor noise required.')
    times = tuple(range(601))
    pat = tuple(200+.1*t for t in times)
    clock = tuple(clock_value(condition,t) for t in times)
    signal_rng = random.Random(seed)
    observed = Observations(times, tuple(p+c+signal_rng.gauss(0,5) for p,c in zip(pat,clock)))
    baseline = score(observed.delay_ms,pat)
    output = {'no_correction': {**baseline, 'corrected_fraction': 0., 'blind_schedule': False},
              'oracle': {**score(tuple(d-c for d,c in zip(observed.delay_ms,clock)),pat),
                         'corrected_fraction': 1., 'blind_schedule': False}}
    schedules = {}
    for method,jitter in (('regular',False),('jittered',True)):
        anchors = schedule(condition.spacing_s,seed,jitter)
        schedules[method] = anchors
        noise_rng = random.Random(2000000+seed)
        clean_values = tuple(clock_value(condition,t) for t in anchors)
        values = tuple(v+noise_rng.gauss(0,condition.anchor_sd_ms) for v in clean_values)
        estimated,sd = interpolate_clock(times,anchors,values,condition.anchor_sd_ms)
        corrected,fraction = selective_correct(observed,estimated,sd,THRESHOLD)
        output[method] = {**score(corrected,pat), 'corrected_fraction': fraction,
                          'blind_schedule': max(abs(x) for x in clean_values)<1e-8 and max(abs(x) for x in clock)>1}
    for method in output:
        output[method]['mae_delta_vs_none_ms'] = output[method]['pat_mae_ms']-baseline['pat_mae_ms']
    return output,schedules


def default_conditions():
    shapes = [('oscillating',period,phase) for period,phase in itertools.product((120,200,300,450),(0,math.pi/4,math.pi/2))]
    shapes += [('none',0,0),('linear',0,0)]
    return [Condition(*shape,spacing,sd) for shape,spacing,sd in itertools.product(shapes,(60,150,300,600),(0,5))]


def run(output, *, conditions=None, seeds=tuple(range(200,220))):
    if len(seeds)<2 or len(set(seeds))!=len(seeds):
        raise ValueError('At least two distinct seeds required.')
    conditions = default_conditions() if conditions is None else conditions
    if not conditions:
        raise ValueError('No conditions.')
    trials,aggregates,anchor_rows = [],[],[]
    for condition in conditions:
        cell=[]
        for seed in seeds:
            metrics,schedules=evaluate(condition,seed)
            paired=metrics['jittered']['pat_mae_ms']-metrics['regular']['pat_mae_ms']
            for method,m in metrics.items():
                row={**asdict(condition),'seed':seed,'method':method,**m,
                     'jitter_minus_regular_mae_ms':paired}
                trials.append(row)
                cell.append(row)
            for method,times in schedules.items():
                anchor_rows.append({**asdict(condition),'seed':seed,'method':method,
                                    'anchor_times_s':json.dumps(times)})
        for method in metrics:
            subset=[r for r in cell if r['method']==method]
            row={**asdict(condition),'method':method,'repeats':len(seeds)}
            for metric in ('pat_mae_ms','endpoint_error_ms','change_distortion_ms','corrected_fraction','blind_schedule','mae_delta_vs_none_ms','jitter_minus_regular_mae_ms'):
                row[metric+'_mean']=fmean(r[metric] for r in subset)
                row[metric+'_sd']=stdev(r[metric] for r in subset)
            row['jitter_better_over_1ms_fraction']=fmean(r['jitter_minus_regular_mae_ms'] < -1 for r in subset)
            row['jitter_worse_over_1ms_fraction']=fmean(r['jitter_minus_regular_mae_ms'] > 1 for r in subset)
            aggregates.append(row)
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in (('trials.csv',trials),('aggregate.csv',aggregates),('schedules.csv',anchor_rows)):
        with (output/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    metadata={'condition_count':len(conditions),'conditions':[asdict(c) for c in conditions],
              'seeds':list(seeds),'threshold':THRESHOLD,'jitter_fraction':JITTER_FRACTION,
              'observation_sd_ms':5,'true_pat':'200+0.1*t ms','duration_s':600,
              'method_evaluations':len(trials),'threshold_origin':'Assignment 05 development selection; no tuning in Assignment 06.',
              'comparison':'Same anchor count; fixed endpoints; shared event noise and anchor noise by index; independent scheduling stream.',
              'limits':'Synthetic profiles; known noise SD; model error excluded from uncertainty; diagnostic blindness uses hidden truth, not available to estimator. 1ms margins are reporting choices, not clinical limits.',
              'python':platform.python_version(),
              'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('experiments/anchor_schedule.py','experiments/selective_correction.py','experiments/paired_timing.py')}}
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return aggregates


def plot(rows,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    labels=('none','linear','oscillating')
    for index,method in enumerate(('no_correction','regular','jittered')):
        vals=[fmean(r['pat_mae_ms_mean'] for r in rows if r['profile']==p and r['method']==method) for p in labels]
        axes[0].bar([i+(index-1)*.25 for i in range(3)],vals,width=.25,label=method.replace('_',' '))
    axes[0].set_xticks(range(3),labels)
    axes[0].set_ylabel('PAT MAE (ms)')
    axes[0].set_title('Per-profile means across specified conditions')
    axes[0].legend()
    for method in ('regular','jittered'):
        selected=[r for r in rows if r['profile']=='oscillating' and r['period_s']==300 and r['phase_rad']==0 and r['anchor_sd_ms']==0 and r['method']==method]
        selected.sort(key=lambda r:r['spacing_s'])
        axes[1].plot([r['spacing_s'] for r in selected],[r['pat_mae_ms_mean'] for r in selected],marker='o',label=method)
    axes[1].set_title('300 s period, zero phase, exact clock anchors')
    axes[1].set_xlabel('Nominal anchor spacing (s)')
    axes[1].set_ylabel('PAT MAE (ms)')
    axes[1].legend()
    axes[1].grid(alpha=.2)
    fig.suptitle('Same measurement count, fixed correction rule; 5 ms event noise')
    fig.savefig(output/'schedules.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('results/assignment-06'))
    args=parser.parse_args()
    result=run(args.output_dir)
    plot(result,args.output_dir)
    print(f'Saved {len(result)} condition/method summaries to {args.output_dir}')
