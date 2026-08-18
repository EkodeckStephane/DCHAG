from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'spec'))
from validate_spec import validate

def test_phase1_specification_contract():
    assert validate() == []
