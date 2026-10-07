"""Regression: a retiring father must not become his son's candidate record."""
import ast, re, unicodedata
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any
# Execute the builder's actual identity functions without network-parser imports.
source=(Path(__file__).resolve().parents[1]/'build_incumbent_records_2026.py').read_text()
tree=ast.parse(source)
names={'norm_name','surname','name_suffix','match_incumbent_candidates','sponsor_match'}
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
ns=dict(re=re,unicodedata=unicodedata,defaultdict=defaultdict,Any=Any)
exec(compile(module,'build_incumbent_records_2026.py','exec'),ns)
m=SimpleNamespace(**ns)
sr={'candidate_name':'Robert E Craven Sr','candidate_id':'house-32-incumbent-robert-e-craven-sr','chamber':'house','district_number':32}
jr={'candidate_name':'Robert E Craven Jr','candidate_id':'house-32-dem-primary-robert-e-craven-jr','chamber':'house','district_number':32}
assert m.match_incumbent_candidates([sr],[jr])==[sr]
other={'candidate_name':'Earl A Read III','candidate_id':'old','chamber':'house','district_number':26}
new=dict(other,candidate_id='house-26-dem-primary-earl-a-read-iii')
assert m.match_incumbent_candidates([other],[new])==[new]
assert m.sponsor_match('Robert E Craven Sr','Craven')  # Bill sponsor lists omit suffixes.
print('PASS: rebuild retains Craven Sr separately, refuses Jr match and preserves bill surname matching')
