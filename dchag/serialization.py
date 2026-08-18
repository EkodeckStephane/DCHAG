from pathlib import Path
from .engine import Trajectory

def save_trajectory(traj:Trajectory,path:str|Path)->None:
    Path(path).write_text(traj.to_json(),encoding="utf-8")

def load_trajectory(path:str|Path)->Trajectory:
    return Trajectory.from_json(Path(path).read_text(encoding="utf-8"))
