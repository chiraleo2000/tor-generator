# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from docx import Document
from docx.text.paragraph import Paragraph

doc = Document('647 จัดซื้อจัดจ้าง.docx')
blocks = []
body = doc.element.body
for child in body:
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        p = Paragraph(child, doc)
        blocks.append(p.text.strip())
    else:
        blocks.append('[T]')

def fnd(m, s, e):
    for i in range(s, e):
        if m in blocks[i]:
            return i, blocks[i][:60]
    return -1, 'NOT FOUND'

def fnds(m, s, e, maxl=25):
    for i in range(s, e):
        if blocks[i] == m or (m in blocks[i] and len(blocks[i]) <= maxl):
            return i, blocks[i][:60]
    return -1, 'NOT FOUND'

# Find chapter starts
i4, _ = fnd('บทที่ 4 กระบวนการ', 300, 800)
i5, _ = fnd('บทที่ 5 การทำสัญญา', i4, 800)
i6, _ = fnd('การบริหารสัญญา', i5, 800)
iA, _ = fnds('ภาคผนวก', i6, 800, 10)

print(f'Ch4={i4}, Ch5={i5}, Ch6={i6}, App={iA}')
print()

tests = [
    ('4.2 def',   fnd('2. วิธีการ', i4, i5)),
    ('4.3 eval',  fnd('3. การพิจารณาคัดเลือก', i4, i5)),
    ('4.1 sub',   fnd('4.1 ', i4, i5)),
    ('4.4 sub',   fnd('4.4 ', i4, i5)),
    ('4.5 sub',   fnd('4.5 ', i4, i5)),
    ('ebid proc', fnd('วิธีประกาศเชิญชวนทั่วไป วิธีประกวดราคา', i4, i5)),
    ('sel proc',  fnds('วิธีคัดเลือก', i4, i5, 15)),
    ('spec proc', fnd('วิธีเฉพาะเจาะจง  เมื่อ', i4, i5)),
    ('auth',      fnd('5. อำนาจ', i4, i5)),
    ('announce',  fnd('6. การประกาศ', i4, i5)),
    ('advance',   fnd('7. ค', i4, i5)),
    # ch5
    ('5.sign',    fnd('1.2', i5, i6)),
    ('5.fine',    fnd('1.3', i5, i6)),
    ('5.sub',     fnd('1.4', i5, i6)),
    ('5.guar',    fnd('2.1', i5, i6)),
    ('5.adv',     fnd('2.2', i5, i6)),
    # ch6
    ('6.inspect', fnd('คณะกรรมการตรวจรับพัสดุในงาน', i6, iA)),
    ('6.amend',   fnd('2. การ', i6, iA)),
    ('6.waive',   fnd('การงดหรือ', i6, iA)),
    ('6.term',    fnd('การบอกเลิก', i6, iA)),
    ('6.agree',   fnd('การตกลงกับ', i6, iA)),
    ('6.bond',    fnd('การคืน', i6, iA)),
    # app
    ('wf_ebid',   fnd('Workflow e-bidding', iA, len(blocks))),
    ('wf_sel',    fnd('Workflow', iA+1, len(blocks))),
    ('timeline',  fnd('ระยะเวลาในการดำเนินการจางทำของ', iA, len(blocks))),
    ('tor_ex',    fnds('ตัวอยาง', iA, len(blocks), 10)),
    ('contract',  fnd('สัญญาเลขที่', iA, len(blocks))),
]
for name, (idx, txt) in tests:
    print(f'  {name:12}: [{idx}] {txt!r}')
