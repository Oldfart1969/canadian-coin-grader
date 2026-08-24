from __future__ import annotations
from pathlib import Path
from PIL import Image
import numpy as np, pandas as pd
from grading_engine import _analyze, _nearest_grade, _label_for, validate_image

HERE=Path(__file__).resolve().parent
REF=pd.read_csv(HERE/'reference_feature_index.csv')
FEATURES=['detail','contrast','surface','luster','marks','exposure_quality']
# Greater weight on luster/surface/marks around AU/MS; exposure is mainly a quality control.
W=np.array([1.25,1.05,1.35,1.55,1.35,0.25],dtype=float)

def _denom_key(d):
    s=str(d).lower().replace('$',' dollar').replace('¢',' cent')
    if '50' in s and 'cent' in s:return '50-cent'
    if '25' in s and 'cent' in s:return '25-cent'
    if '10' in s and 'cent' in s:return '10-cent'
    if '5' in s and 'cent' in s:return '5-cent'
    if '1' in s and ('dollar' in s or 'piastre' in s):return '1-dollar'
    if '1' in s and 'cent' in s:return '1-cent'
    return str(d)

def _era_distance(y, ry):
    try:return abs(int(str(y)[:4])-int(str(ry)[:4]))
    except:return 99

def _reference_estimate(avg, denomination, year):
    d=_denom_key(denomination)
    pool=REF[REF.denomination==d].copy()
    if pool.empty:return None
    pool['era_dist']=[_era_distance(year,x) for x in pool.year]
    # Prefer same/near years but keep enough grade anchors.
    near=pool[pool.era_dist<=8]
    if len(near)>=18: pool=near
    X=pool[FEATURES].to_numpy(float)
    q=np.array([avg[k] for k in FEATURES],float)
    # Robust feature scaling learned from reference corpus.
    scale=np.maximum(REF[FEATURES].std().to_numpy(float),0.08)
    dist=np.sqrt(np.sum((((X-q)/scale)*W)**2,axis=1)) + 0.015*pool.era_dist.to_numpy(float)
    pool=pool.assign(distance=dist).sort_values('distance').head(11)
    # Distance-weighted median-ish estimate; top matches dominate without a single outlier controlling result.
    weights=1/(pool.distance.to_numpy(float)+0.10)**2
    grades=pool.grade.to_numpy(float)
    order=np.argsort(grades); grades=grades[order]; weights=weights[order]
    c=np.cumsum(weights)/weights.sum(); est=float(grades[np.searchsorted(c,.5)])
    # local weighted mean softens discrete jumps
    mean=float(np.average(pool.grade,weights=1/(pool.distance+0.12)))
    est=.65*est+.35*mean
    return est,pool

def _heuristic(avg):
    preservation=.34*avg['detail']+.23*avg['contrast']+.19*avg['surface']+.14*avg['luster']+.10*(1-avg['marks'])
    if preservation<.18:return 3+preservation/.18*5
    if preservation<.32:return 8+(preservation-.18)/.14*12
    if preservation<.46:return 20+(preservation-.32)/.14*20
    if preservation<.60:return 40+(preservation-.46)/.14*18
    mint=.28*avg['surface']+.25*(1-avg['marks'])+.20*avg['detail']+.17*avg['luster']+.10*avg['contrast']
    return 58+10*np.clip((mint-.38)/.50,0,1)

def _side_score(a, denomination, year):
    r=_reference_estimate(a,denomination,year)
    return r[0] if r else _heuristic(a)

def grade_coin_v2(obv:Image.Image, rev:Image.Image, denomination, year, strike='Business strike'):
    a,b=_analyze(obv),_analyze(rev); avg={k:(a[k]+b[k])/2 for k in a}
    h=_heuristic(avg); rr=_reference_estimate(avg,denomination,year)
    if rr:
        ref_est,matches=rr; numeric=.72*ref_est+.28*h
        # AU/MS gate: if nearest neighborhood is mostly AU and luster is weak, do not jump to MS.
        top5=matches.head(5)
        au_share=float(np.mean(top5.grade<60)); ms_share=1-au_share
        if numeric>=60 and au_share>=.60 and avg['luster']<.62: numeric=min(numeric,58.4)
        if numeric<60 and ms_share>=.80 and avg['luster']>.58 and avg['surface']>.48: numeric=max(numeric,60.0)
    else:
        matches=None; numeric=h
    # Focal-side limiter: one materially weaker face constrains whole coin.
    so,sr=_side_score(a,denomination,year),_side_score(b,denomination,year)
    weaker=min(so,sr)
    if numeric>=60 and weaker<numeric-2.2:numeric=min(numeric,weaker+1.5)
    numeric=float(np.clip(numeric,1,67))
    _,grade=_nearest_grade(numeric,strike)
    # confidence from photo quality + reference proximity/agreement
    agreement=1-min(1,abs(so-sr)/10)
    photo=.45*avg['detail']+.35*avg['exposure_quality']+.20*agreement
    refq=0.45
    if matches is not None:
        refq=float(np.clip(1-matches.distance.head(5).mean()/5.0,.15,.95))
    confidence=float(np.clip(.38+.25*photo+.30*refq,.40,.90))
    spread=3 if numeric<40 else (2 if numeric<60 else (1 if confidence>.72 else 1.5))
    low,high=_label_for(numeric-spread,strike),_label_for(numeric+spread,strike)
    comps=[]
    if matches is not None:
        for _,r in matches.head(5).iterrows():
            comps.append({'grade':int(r.grade),'grade_label':r.grade_label,'year':str(r.year),'file':r.file,'distance':round(float(r.distance),3)})
    reasons=[]
    if numeric>=60:
        reasons.append('Le modèle classe la pièce dans la zone non circulée; le sous-grade est surtout déterminé par les surfaces, le lustre et les marques.')
    elif numeric>=50: reasons.append("La pièce se situe dans la zone AU: légère friction/usure possible sur les points hauts, mais détails presque complets.")
    else: reasons.append("Le grade est principalement limité par l'usure et la perte de détails observées par rapport aux références circulées.")
    if abs(so-sr)>=2: reasons.append("Les deux faces ne sont pas de force égale; la face la plus faible limite le grade global.")
    return {'grade':grade,'numeric_grade':round(numeric,2),'confidence':confidence,'range':(low,high),
            'side_estimates':{'obverse':_label_for(so,strike),'reverse':_label_for(sr,strike),'obverse_numeric':round(so,1),'reverse_numeric':round(sr,1)},
            'metrics':{'detail':round(avg['detail']*10,1),'surface':round(avg['surface']*10,1),'contrast':round(avg['contrast']*10,1),'luster':round(avg['luster']*10,1),'marks_quality':round((1-avg['marks'])*10,1)},
            'comparables':comps,'reasons':reasons,'meta':{'denomination':denomination,'year':year,'strike':strike,'reference_count':int(len(REF))}}
