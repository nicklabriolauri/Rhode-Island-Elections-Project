"""Regression checks for historical names sharing a surname."""
from build_candidate_pages import candidate_name_matches
assert candidate_name_matches('Enrique George Sanchez','Enrique G. Sanchez')
assert candidate_name_matches('Enrique George Sanchez','Enrique George Sanchez')
assert not candidate_name_matches('Enrique George Sanchez','Ana Aljeimy SANTANA-SANCHEZ')
assert not candidate_name_matches('Anthony J DeSimone','John J. DeSimone')
assert candidate_name_matches('Anthony J DeSimone','Anthony J. DeSimone')
assert candidate_name_matches('Ramon Perez','Ramón Pérez*')
assert not candidate_name_matches('Ramon Perez','Carlos Perez')
print('PASS: middle-name aliases preserved; different candidates with shared surnames rejected')
