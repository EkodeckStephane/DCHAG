from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import hashlib, json
import yaml
from .errors import ConfigError

ALLOWED_TYPES={"human","process","technical","control","context"}
ATTACK_TYPES={"human","process","technical"}
ALLOWED_EQUATIONS={"logistic_bernoulli","deterministic_threshold"}

@dataclass(frozen=True)
class ParentSpec:
    node: str
    coef: float
    lag: int = 0

@dataclass(frozen=True)
class NodeSpec:
    id: str
    type: str
    intercept: float
    parents: tuple[ParentSpec,...]=()
    equation: str="logistic_bernoulli"
    threshold: float=0.5

@dataclass(frozen=True)
class ModelConfig:
    name: str
    horizon: int
    nodes: tuple[NodeSpec,...]
    target: str
    baseline_controls: dict[str,int]
    metadata: dict

    @property
    def node_map(self):
        return {n.id:n for n in self.nodes}

    @property
    def controls(self):
        return tuple(n.id for n in self.nodes if n.type=="control")

    @property
    def attack_nodes(self):
        return tuple(n.id for n in self.nodes if n.type in ATTACK_TYPES)


def _parse(data: dict) -> ModelConfig:
    nodes=[]
    for n in data.get("nodes",[]):
        parents=tuple(ParentSpec(node=p["node"],coef=float(p["coef"]),lag=int(p.get("lag",0))) for p in n.get("parents",[]))
        nodes.append(NodeSpec(id=n["id"], type=n["type"], intercept=float(n.get("intercept",0.0)), parents=parents,
                              equation=n.get("equation","logistic_bernoulli"), threshold=float(n.get("threshold",0.5))))
    cfg=ModelConfig(name=data["name"], horizon=int(data["horizon"]), nodes=tuple(nodes), target=data["target"],
                    baseline_controls={k:int(v) for k,v in data.get("baseline_controls",{}).items()}, metadata=data.get("metadata",{}))
    validate_config(cfg)
    return cfg


def load_config(path: str|Path) -> ModelConfig:
    path=Path(path)
    return _parse(yaml.safe_load(path.read_text(encoding="utf-8")))


def validate_config(cfg: ModelConfig) -> None:
    if cfg.horizon < 1:
        raise ConfigError("horizon must be >=1")
    ids=[n.id for n in cfg.nodes]
    if len(ids)!=len(set(ids)):
        raise ConfigError("duplicate node identifiers")
    idx={node:i for i,node in enumerate(ids)}
    node_map=cfg.node_map
    if cfg.target not in node_map:
        raise ConfigError("target variable absent from graph")
    if node_map[cfg.target].type!="technical":
        raise ConfigError("target must be a technical state")
    for n in cfg.nodes:
        if n.type not in ALLOWED_TYPES:
            raise ConfigError(f"unknown node type: {n.type}")
        if n.equation not in ALLOWED_EQUATIONS:
            raise ConfigError(f"unknown equation: {n.equation}")
        for p in n.parents:
            if p.node not in node_map:
                raise ConfigError(f"invalid parent reference: {p.node}")
            if p.lag < 0:
                raise ConfigError("negative lag")
            if p.lag==0:
                if p.node==n.id:
                    raise ConfigError("same-slice self loop")
                if idx[p.node] >= idx[n.id]:
                    raise ConfigError(f"same-slice parent {p.node} must precede {n.id}")
    for c,v in cfg.baseline_controls.items():
        if c not in node_map or node_map[c].type!="control":
            raise ConfigError(f"baseline control is undeclared: {c}")
        if v not in (0,1):
            raise ConfigError("control values must be binary")


def config_sha256(path: str|Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
