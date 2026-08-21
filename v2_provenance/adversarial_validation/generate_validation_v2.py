from __future__ import annotations
from pathlib import Path
import argparse, json
import numpy as np
from adversarial_validation.common import link_probability, flatten_frame, write_json, sha256

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks" / "validation_v2"
PUBLIC = BASE / "public"
PRIVATE = BASE / "private_worlds"

FAMILIES = {
"helpdesk": {
 "contexts":["high_risk_context","operational_pressure"],
 "controls":["strong_verification","mfa_enforcement","manager_callback","session_risk_block"],
 "early":["malicious_reset_request","social_engineering_signal"],
 "humans":["approve_reset","override_warning","escalate_identity_check"],
 "processes":["reset_authorized","identity_escalation","credential_issue"],
 "technical":["credential_compromised","privileged_access","anomalous_session","compromise"]},
"bec": {
 "contexts":["payment_urgency","operational_pressure"],
 "controls":["dual_authorization","out_of_band_verify","payment_hold","sender_auth"],
 "early":["spoofed_message","mailbox_anomaly"],
 "humans":["trust_sender","approve_payment","override_hold"],
 "processes":["invoice_validated","payment_released","finance_escalation"],
 "technical":["beneficiary_changed","transfer_attempt","mailbox_compromised","compromise"]},
"exfiltration": {
 "contexts":["sensitive_project","operational_pressure"],
 "controls":["dlp_block","manager_approval","media_block","privileged_review"],
 "early":["suspicious_access","bulk_read_signal"],
 "humans":["accept_export","approve_exception","ignore_alert"],
 "processes":["export_request","exception_ticket","data_release"],
 "technical":["data_staged","archive_ready","egress_attempt","compromise"]},
"itot": {
 "contexts":["critical_window","operational_pressure"],
 "controls":["change_control","jump_host","firmware_signing","network_segmentation"],
 "early":["remote_session","unsafe_command"],
 "humans":["authorize_change","approve_override","acknowledge_alarm"],
 "processes":["work_order","maintenance_window","emergency_override"],
 "technical":["device_write","unsafe_state","lateral_move","compromise"]},
}


def edge(parent, lag, coef): return {"node":parent,"lag":lag,"coef":float(coef)}
def inter(a, la, b, lb, coef): return {"a":a,"lag_a":la,"b":b,"lag_b":lb,"coef":float(coef)}


def make_world(family: str, seed: int, *, latent: bool=False):
    rng=np.random.default_rng(seed); f=FAMILIES[family]
    # Vary node counts and therefore topology across independent worlds.
    nh=int(rng.integers(2,4)); np_=int(rng.integers(2,4)); ne=int(rng.integers(1,3)); ntmid=int(rng.integers(2,4))
    contexts=f["contexts"]
    controls=f["controls"]
    early=f["early"][:ne]
    humans=f["humans"][:nh]
    processes=f["processes"][:np_]
    mids=f["technical"][:-1][:ntmid]
    target="compromise"
    order=contexts+controls+early+humans+processes+mids+[target]
    types={x:"context" for x in contexts}|{x:"control" for x in controls}|{x:"technical" for x in early+mids+[target]}|{x:"human" for x in humans}|{x:"process" for x in processes}
    horizon=int(rng.integers(4,7))
    nodes=[]
    # persistent exogenous-looking contexts; pressure is treatment/confounder feedback carrier.
    nodes.append({"id":contexts[0],"type":"context","intercept":float(rng.uniform(-0.8,-0.2)),"link":"probit",
                  "parents":[edge(contexts[0],1,float(rng.uniform(1.3,2.1)))],"interactions":[]})
    pressure_par=[edge(contexts[0],0,float(rng.uniform(.6,1.2))), edge(contexts[1],1,float(rng.uniform(1.1,1.9)))]
    # prior defensive action can affect next operational pressure (treatment-confounder feedback)
    pressure_par.append(edge(controls[0],1,float(rng.uniform(-.8,-.35))))
    nodes.append({"id":contexts[1],"type":"context","intercept":float(rng.uniform(-1.0,-.4)),"link":"cloglog",
                  "parents":pressure_par,"interactions":[]})
    # Controls are persistent and preferentially deployed in risky/pressured histories.
    for i,c in enumerate(controls):
        pars=[edge(contexts[0],0,float(rng.uniform(.5,1.0))),edge(contexts[1],0,float(rng.uniform(.45,.9))),edge(c,1,float(rng.uniform(2.2,3.2)))]
        if i>0: pars.append(edge(controls[i-1],1,float(rng.uniform(.2,.55))))
        nodes.append({"id":c,"type":"control","intercept":float(rng.uniform(-2.0,-1.2)),"link":"logistic","parents":pars,"interactions":[]})
    # Early attack indicators.
    for i,nid in enumerate(early):
        pars=[edge(contexts[0],0,float(rng.uniform(.8,1.4))), edge(contexts[1],0,float(rng.uniform(.4,.8))), edge(nid,1,float(rng.uniform(.7,1.4)))]
        pars.append(edge(controls[(i+1)%4],0,float(rng.uniform(-1.3,-.6))))
        nodes.append({"id":nid,"type":"technical","intercept":float(rng.uniform(-1.7,-.9)),"link":rng.choice(["probit","cloglog"]),"parents":pars,
                      "interactions":[inter(contexts[0],0,controls[(i+1)%4],0,float(rng.uniform(-.7,-.25)))]})
    # Human branch: each node gets attack signal + context + one/two controls, with interaction.
    for i,nid in enumerate(humans):
        source=early[i%len(early)]
        pars=[edge(source,0,float(rng.uniform(1.4,2.4))),edge(contexts[1],0,float(rng.uniform(.45,.9))),edge(controls[i%4],0,float(rng.uniform(-1.7,-.8))),edge(nid,1,float(rng.uniform(.4,1.0)))]
        if i>0: pars.append(edge(humans[i-1],0,float(rng.uniform(.45,.9))))
        nodes.append({"id":nid,"type":"human","intercept":float(rng.uniform(-2.1,-1.2)),"link":rng.choice(["probit","soft_threshold"]),"parents":pars,
                      "interactions":[inter(source,0,controls[i%4],0,float(rng.uniform(-1.0,-.45)))]})
    # Process branch with branching/cross-links.
    for i,nid in enumerate(processes):
        h1=humans[i%len(humans)]; h2=humans[(i+1)%len(humans)]
        pars=[edge(h1,0,float(rng.uniform(1.2,2.1))),edge(controls[(i+2)%4],0,float(rng.uniform(-1.5,-.65))),edge(contexts[1],1,float(rng.uniform(.3,.7)))]
        if h2!=h1: pars.append(edge(h2,0,float(rng.uniform(.35,.75))))
        if i>0: pars.append(edge(processes[i-1],0,float(rng.uniform(.55,1.0))))
        nodes.append({"id":nid,"type":"process","intercept":float(rng.uniform(-2.0,-1.0)),"link":rng.choice(["logistic","cloglog","probit"]),"parents":pars,
                      "interactions":[inter(h1,0,contexts[1],0,float(rng.uniform(.35,.8)))]})
    # Technical middle states get multiple process branches and persistent risk.
    for i,nid in enumerate(mids):
        p1=processes[i%len(processes)]; p2=processes[(i+1)%len(processes)]
        pars=[edge(p1,0,float(rng.uniform(1.3,2.2))),edge(controls[(i+1)%4],0,float(rng.uniform(-1.8,-.8))),edge(nid,1,float(rng.uniform(.7,1.5)))]
        if p2!=p1: pars.append(edge(p2,0,float(rng.uniform(.4,.9))))
        if i>0: pars.append(edge(mids[i-1],0,float(rng.uniform(.55,1.1))))
        nodes.append({"id":nid,"type":"technical","intercept":float(rng.uniform(-2.3,-1.2)),"link":rng.choice(["probit","soft_threshold","logistic"]),"parents":pars,
                      "interactions":[inter(p1,0,controls[(i+1)%4],0,float(rng.uniform(-1.0,-.35)))]})
    # Target has at least two branches, direct control effects, memory and operational pressure.
    pars=[edge(m,0,float(rng.uniform(1.0,1.8))) for m in mids]
    pars += [edge(humans[-1],0,float(rng.uniform(.45,.9))), edge(contexts[1],0,float(rng.uniform(.45,.8))), edge(target,1,float(rng.uniform(1.0,1.8)))]
    pars += [edge(controls[2],0,float(rng.uniform(-1.5,-.7))), edge(controls[3],0,float(rng.uniform(-1.4,-.6)))]
    ints=[inter(mids[0],0,mids[-1],0,float(rng.uniform(.45,.9))), inter(contexts[1],0,controls[3],0,float(rng.uniform(-.8,-.3)))]
    nodes.append({"id":target,"type":"technical","intercept":float(rng.uniform(-2.8,-1.7)),"link":rng.choice(["probit","cloglog","soft_threshold"]),"parents":pars,"interactions":ints})
    return {"family":family,"seed":seed,"latent":latent,"horizon":horizon,"target":target,"controls":controls,"baseline_controls":{c:0 for c in controls},"order":order,"types":types,"nodes":nodes,
            "latent_spec":{"phi":.82,"control_coef":.75,"risk_coef":.9} if latent else None}


def _parent_value(states, idx, t, parent, lag):
    pt=t-lag
    if pt<0:return 0.0
    return states[:,pt,idx[parent]]


def simulate(world, n, seed, interventions=None, *, return_latent=False):
    rng=np.random.default_rng(seed); order=world["order"]; idx={x:i for i,x in enumerate(order)}; h=world["horizon"]
    states=np.zeros((n,h,len(order)),dtype=np.int8); interventions=interventions or {}
    uniforms=rng.random((n,h,len(order)),dtype=np.float64)
    U=np.zeros((n,h),dtype=float)
    if world["latent"]:
        eps=rng.normal(size=(n,h)); U[:,0]=eps[:,0]
        phi=world["latent_spec"]["phi"]
        for t in range(1,h): U[:,t]=phi*U[:,t-1]+np.sqrt(1-phi**2)*eps[:,t]
    node_map={z["id"]:z for z in world["nodes"]}
    for t in range(h):
        for nid in order:
            j=idx[nid]; node=node_map[nid]
            if node["type"]=="control" and nid in interventions:
                states[:,t,j]=int(interventions[nid]); continue
            eta=np.full(n,node["intercept"],float)
            for p in node["parents"]:
                eta += p["coef"]*_parent_value(states,idx,t,p["node"],p["lag"])
            for z in node["interactions"]:
                a=_parent_value(states,idx,t,z["a"],z["lag_a"]); b=_parent_value(states,idx,t,z["b"],z["lag_b"])
                eta += z["coef"]*a*b
            if world["latent"]:
                if node["type"]=="control": eta += world["latent_spec"]["control_coef"]*U[:,t]
                if nid==world["target"] or node["type"]=="human": eta += world["latent_spec"]["risk_coef"]*U[:,t]
            p=link_probability(eta,node["link"])
            states[:,t,j]=(uniforms[:,t,j]<p).astype(np.int8)
    return (states,U) if return_latent else states


def public_schema(world):
    return {k:world[k] for k in ["family","horizon","target","controls","baseline_controls","order","types"]}


def generate_one(tag,family,seed,latent,ntrain,ntest):
    w=make_world(family,seed,latent=latent); pub=PUBLIC/tag; prv=PRIVATE/tag; pub.mkdir(parents=True,exist_ok=True);prv.mkdir(parents=True,exist_ok=True)
    train=simulate(w,ntrain,seed+10001); test=simulate(w,ntest,seed+20001)
    flatten_frame(train,w["order"]).to_csv(pub/"train.csv",index=False)
    flatten_frame(test,w["order"]).to_csv(pub/"test.csv",index=False)
    write_json(pub/"schema.json",public_schema(w)); write_json(prv/"world.json",w)
    # true observable edge set is private and only scored after estimator freeze
    edges=[]
    for node in w["nodes"]:
        for p in node["parents"]: edges.append([p["node"],p["lag"],node["id"]])
        for z in node["interactions"]:
            edges.append([z["a"],z["lag_a"],node["id"]]); edges.append([z["b"],z["lag_b"],node["id"]])
    write_json(prv/"true_edges.json",sorted({tuple(x) for x in edges}))
    write_json(pub/"data_manifest.json",{"train_sha256":sha256(pub/"train.csv"),"test_sha256":sha256(pub/"test.csv"),"schema_sha256":sha256(pub/"schema.json"),"ntrain":ntrain,"ntest":ntest})
    return w


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--stage",choices=["development","confirmatory","latent","all"],default="all");a=ap.parse_args()
    BASE.mkdir(parents=True,exist_ok=True)
    fams=list(FAMILIES)
    if a.stage in {"development","all"}:
        for i,f in enumerate(fams): generate_one(f"dev_{f}",f,4100+97*i,False,900,350)
    if a.stage in {"confirmatory","all"}:
        for fi,f in enumerate(fams):
            for r in range(4): generate_one(f"confirm_{f}_{r+1}",f,11000+1000*fi+137*r,False,1600,500)
    if a.stage in {"latent","all"}:
        for fi,f in enumerate(fams):
            # Matched seed/topology to confirm_*_1, with hidden common cause added.
            generate_one(f"latent_{f}_1",f,11000+1000*fi,True,1600,500)
    print("generated",a.stage)

if __name__=="__main__": main()
