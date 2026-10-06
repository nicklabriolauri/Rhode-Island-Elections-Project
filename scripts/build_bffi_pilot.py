"""Apply the verified BFFI pilot to Lauria while preserving the rest of her profile."""
from candidate_profile_components import ROOT,load,replace_section,ratings,bffi_styles

def build():
 slug='pamela-j-lauria'
 record=next(r for r in load('incumbent_records_2026')['records'] if r['candidate_id']=='senate-32-dem-primary-'+slug)
 path=ROOT/'candidates'/f'{slug}.html'
 page=replace_section(path.read_text(),'ratings',ratings(record))
 path.write_text(bffi_styles(page,record))

if __name__=='__main__':build()
