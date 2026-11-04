from pathlib import Path
import os,sys,re,io,json,hashlib,html,unicodedata
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'build'/'matplotlib_cache')
(ROOT/'build').mkdir(exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pymupdf
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,PageBreak,Image,Table,TableStyle,KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY,TA_CENTER,TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
for name,file in [('ReportRoman','times.ttf'),('ReportBold','timesbd.ttf'),('ReportItalic','timesi.ttf'),('ReportBoldItalic','timesbi.ttf')]:
 pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
pdfmetrics.registerFontFamily('ReportRoman',normal='ReportRoman',bold='ReportBold',italic='ReportItalic',boldItalic='ReportBoldItalic')
S={
 'body':ParagraphStyle('Body',fontName='ReportRoman',fontSize=11,leading=15.1,alignment=TA_JUSTIFY,spaceAfter=8,splitLongWords=True),
 'h1':ParagraphStyle('Heading1',fontName='ReportBold',fontSize=20,leading=25,spaceBefore=10,spaceAfter=19,keepWithNext=True),
 'h2':ParagraphStyle('Heading2',fontName='ReportBold',fontSize=13.4,leading=17.5,spaceBefore=13,spaceAfter=8,keepWithNext=True),
 'h3':ParagraphStyle('Heading3',fontName='ReportBold',fontSize=11.8,leading=15,spaceBefore=11,spaceAfter=7,keepWithNext=True),
 'caption':ParagraphStyle('Caption',fontName='ReportRoman',fontSize=9.5,leading=12.2,alignment=TA_CENTER,spaceBefore=6,spaceAfter=11),
 'cell':ParagraphStyle('Cell',fontName='ReportRoman',fontSize=8.8,leading=11.1,spaceAfter=0,splitLongWords=True),
 'cellh':ParagraphStyle('CellHeader',fontName='ReportBold',fontSize=8.8,leading=11.1,spaceAfter=0,splitLongWords=True),
 'ref':ParagraphStyle('Reference',fontName='ReportRoman',fontSize=10,leading=13.8,spaceAfter=10,splitLongWords=True),
 'cover':ParagraphStyle('Cover',fontName='ReportRoman',fontSize=12,leading=17,alignment=TA_CENTER,spaceAfter=12),
 'title':ParagraphStyle('Title',fontName='ReportBold',fontSize=20,leading=25,alignment=TA_CENTER,spaceAfter=17),
 'list':ParagraphStyle('List',fontName='ReportRoman',fontSize=10.7,leading=14.8,leftIndent=15,firstLineIndent=-12,spaceAfter=5),
}
W,H=A4; LEFT=64; RIGHT=54; TOP=57; BOTTOM=52; CW=W-LEFT-RIGHT; CH=H-TOP-BOTTOM
assets=ROOT/'assets'; evidence=ROOT/'evidence'; case=json.loads((evidence/'phase1_retained.json').read_text())
# Evidence plots: no generated or invented experimental values.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,ax=plt.subplots(figsize=(7.4,3.6));x=[0,1];a=[1529,1563];r=[1471,1437]
ax.bar([i-.18 for i in x],a,.36,label='Approved',color='#385c49');ax.bar([i+.18 for i in x],r,.36,label='Rejected',color='#a45b4f');ax.set_xticks(x,['Home loan','Personal loan']);ax.set_ylabel('Synthetic records');ax.set_ylim(0,1850);ax.legend(frameon=False,ncol=2);ax.spines[['top','right']].set_visible(False)
for container in ax.containers:ax.bar_label(container,padding=3)
fig.tight_layout();fig.savefig(assets/'class_counts.png',dpi=180);plt.close(fig)
for method,name,label in [('shap','shap_case','SHAP contribution (raw margin / log-odds)'),('lime','lime_case','LIME local-surrogate weight')]:
 vals=case[method];keys=sorted(vals,key=lambda k:abs(vals[k]));fig,ax=plt.subplots(figsize=(7.6,4.0));v=[vals[k] for k in keys]
 ax.barh([k.replace('_',' ') for k in keys],v,color=['#375e51' if z>=0 else '#aa5649' for z in v]);ax.axvline(0,color='#777',lw=.7);ax.set_xlabel(label);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(assets/(name+'.png'),dpi=180);plt.close(fig)
# Render SVG without editing original bytes.
svg=pymupdf.open(assets/'methodology.svg');svg[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(assets/'methodology_render.png')
# Application template specimen uses retained result, not a new model run.
REPO = ROOT.parent if (ROOT.parent/'backend').exists() else ROOT.parent/'trustfin-ai-prototype-r2'
sys.path.insert(0,str(REPO))
from backend.app.reporting.pdf_generator import generate_loan_report_pdf
specimen=generate_loan_report_pdf(case['applicant'],case['prediction'])
(assets/'application_report_specimen.pdf').write_bytes(specimen)
p=pymupdf.open(stream=specimen,filetype='pdf');p[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(assets/'application_report.png')

def esc(s):
 s=html.escape(s).replace('`','')
 return s

def inline(s):
 s=esc(s)
 s=re.sub(r'\[(\d+(?:,\s*\d+)*)\]',lambda m:'['+', '.join('<link href="#ref-'+n.strip()+'">'+n.strip()+'</link>' for n in m.group(1).split(','))+']',s)
 return s

def roman(n):
 vals=[(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')];out=''
 for v,s in vals:
  while n>=v:out+=s;n-=v
 return out

def page_label(doc):
 return doc.page-doc.body_start+1 if doc.body_start else -(doc.page-1)
class ReportDoc(BaseDocTemplate):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);self.body_start=None;self.running='';self.entries=[]
 def beforeDocument(self):self.body_start=None;self.running='';self.entries=[]
 def afterFlowable(self,f):
  if hasattr(f,'anchor'):
   key=f.anchor;self.canv.bookmarkPage(key)
   if getattr(f,'is_chapter_one',False) and self.body_start is None:self.body_start=self.page
   if getattr(f,'outline',False):self.canv.addOutlineEntry(f.plain,key,level=0,closed=False)
   if getattr(f,'toc_level',None) is not None:
    self.notify('TOCEntry',(f.toc_level,f.plain,page_label(self),key))
   if getattr(f,'list_kind',None):self.notify(f.list_kind,(0,f.plain,page_label(self),key))
   if getattr(f,'running',None):self.running=f.running

def footer(c,doc):
 if doc.page==1:return
 c.saveState();c.setFont('ReportRoman',8);c.setFillColor(colors.HexColor('#555555'));c.drawString(LEFT,H-34,'TrustFin AI');c.drawRightString(W-RIGHT,H-34,'Group Project Report');c.setStrokeColor(colors.HexColor('#999999'));c.setLineWidth(.4);c.line(LEFT,H-40,W-RIGHT,H-40);c.drawCentredString(W/2,30,roman(-page_label(doc)) if page_label(doc)<0 else str(page_label(doc)));c.restoreState()

class Index(TableOfContents):
 def __init__(self,event='TOCEntry'):
  super().__init__();self.event=event;self.formatter=lambda n: roman(-n) if n<0 else str(n)
 def notify(self,kind,stuff):
  if kind==self.event:self.addEntry(*stuff)

def make_index(event):
 t=Index(event);t.levelStyles=[ParagraphStyle('Index0'+event,fontName='ReportRoman',fontSize=10,leading=12,leftIndent=0,firstLineIndent=0,spaceBefore=3),ParagraphStyle('Index1'+event,fontName='ReportRoman',fontSize=9.1,leading=10.5,leftIndent=13,firstLineIndent=0,spaceBefore=0)];t.tableStyle=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),.5),('BOTTOMPADDING',(0,0),(-1,-1),.5),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]);return t

source=(ROOT/'TrustFin_AI_Report_v2.md').read_text(encoding='utf-8'); lines=source.splitlines()
story=[];tex=[];chapter='0';table_counts={};eqnum=0;fig_inventory=[];table_inventory=[];heading_inventory=[];idx=0;in_cover=False
tex_header=r'''\documentclass[12pt,a4paper]{report}
\usepackage[margin=25mm]{geometry}
\usepackage{fontspec}\setmainfont{TeX Gyre Termes}
\usepackage{graphicx,amsmath,longtable,booktabs,array,hyperref,xurl}
\hypersetup{hidelinks}
\setcounter{tocdepth}{1}
\begin{document}
'''
tex.append(tex_header)
def tx(s):
 out=''
 for ch in s:
  out+= {'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(ch,ch)
 return out

def heading(label,level,key):
 f=Paragraph(esc(label),S['h'+str(level)]);f.anchor=key;f.plain=label;f.toc_level=0 if level==1 else (1 if level==2 else None);f.outline=level==1;f.is_chapter_one=label.startswith('Chapter 1 ');f.running=label;story.append(f);heading_inventory.append(label)

def cover():
 story.extend([Spacer(1,35),Paragraph("K. K. Wagh Education Society's",S['cover']),Paragraph('K. K. Wagh Institute of Engineering Education &amp; Research',S['cover']),Paragraph('Department of Information Technology',S['cover']),Spacer(1,20),Paragraph('GROUP PROJECT REPORT',S['cover']),Paragraph('Explainable AI Framework with Explanation Validation for Financial Decision Support',S['title']),Paragraph('TrustFin AI',S['cover']),Paragraph('Submitted in partial fulfilment of the requirements for the degree of<br/>Bachelor of Technology in Information Technology',S['cover']),Spacer(1,9),Paragraph('Ashwin Patil (46) &nbsp;&nbsp; Aaditya Patil (44)<br/>Kanad Nerkar (41) &nbsp;&nbsp; Ved Kalantri (28)',S['cover']),Paragraph('Project Guide: Prof. Rupali M. Bora',S['cover']),Spacer(1,10),Paragraph('Academic Year 2026-2027',S['cover'])])
 tex.append(r'\begin{titlepage}\centering '+tx("K. K. Wagh Institute of Engineering Education & Research")+r'\par\vspace{2cm}{\Large '+tx('Explainable AI Framework with Explanation Validation for Financial Decision Support')+r'}\par\vspace{1cm}TrustFin AI\par Group Project Report\par\vspace{1cm}Ashwin Patil (46), Aaditya Patil (44), Kanad Nerkar (41), Ved Kalantri (28)\par Project Guide: Prof. Rupali M. Bora\par Academic Year 2026-2027\end{titlepage}')

captions={
 '2.1':'Literature and its relationship to TrustFin AI','3.1':'Functional requirements and prototype realization','4.1':'Conceptual design to prototype mapping','4.2':'Implemented persistence entities','4.3':'Implemented API routes','5.1':'Product input field groups','5.2':'Project solvency bands','5.3':'Active frontend responsibilities','6.1':'Additional existing batch checks','6.2':'API and persistence verification','7.1':'Generated dataset summary','7.2':'Saved product held-out metrics','7.3':'Retained worked-case diagnostic values','7.4':'Executed approved/insolvent cases','8.1':'Git-supported development chronology','8.2':'Chronological activity chart','A.1':'Observed verification environment','B.1':'Source and evidence map'}
maths={
 'EMI = P r(1+r)^n / ((1+r)^n - 1)':r'\mathrm{EMI}=P\,\frac{r(1+r)^n}{(1+r)^n-1}',
 'FOIR = (Existing_EMI + Monthly_EMI) / I':r'\mathrm{FOIR}=\frac{\mathrm{Existing\ EMI}+\mathrm{Proposed\ EMI}}{I}',
 'LTV_percent = 100 Loan_Amount / Property_Value':r'\mathrm{LTV}(\%)=100\,\frac{\mathrm{Loan\ Amount}}{\mathrm{Property\ Value}}',
 'q = abs(p - pm) / max(0.08, abs(p - p0))':r'q=\frac{|p-p_m|}{\max(0.08,|p-p_0|)}',
 'F = max(0.02, 2q) for q <= 0.05':r'F=\max(0.02,2q),\quad q\leq 0.05',
 'F = 0.74 + 0.17(1 - exp(-q)) for q > 0.05':r'F=0.74+0.17(1-e^{-q}),\quad q>0.05',
 'S = (rho + 1) / 2':r'S=\frac{\rho+1}{2}',
 'C = size(A3 intersection B3) / size(A3 union B3)':r'C=\frac{|A_3\cap B_3|}{|A_3\cup B_3|}',
 'R = clip(1 - abs(p(x) - p(xg)), 0, 1)':r'R=\max(0,\min(1,1-|p(x)-p(x^{(g)})|))',
 'T = 0.35F + 0.25S + 0.30C + 0.10R':r'T=0.35F+0.25S+0.30C+0.10R',
 'Q = p if yhat = 1; otherwise Q = 1 - p':r'Q=p\ \mathrm{if}\ \hat{y}=1;\quad Q=1-p\ \mathrm{otherwise}'
}
while idx<len(lines):
 line=lines[idx].strip()
 if not line:idx+=1;continue
 if line=='# Cover':in_cover=True;cover();idx+=1;continue
 if in_cover and not line.startswith('# '):idx+=1;continue
 if line.startswith('# '):
  in_cover=False;label=line[2:];story.append(PageBreak())
  m=re.match(r'(\d) (.+)',label)
  if m:
   chapter=m.group(1);eqnum=0;heading('Chapter '+chapter+' - '+m.group(2),1,'chapter-'+chapter);tex.append('\\chapter{'+tx(m.group(2))+'}')
  else:
   if label.startswith('Appendix '):chapter=label.split()[1]
   heading(label,1,'front-'+str(idx));tex.append('\\chapter*{'+tx(label)+'}\\addcontentsline{toc}{chapter}{'+tx(label)+'}')
  idx+=1;continue
 if line.startswith('##'):
  level=3 if line.startswith('###') else 2;label=line.lstrip('# ');key='section-'+label.split()[0];heading(label,level,key)
  title=re.sub(r'^\d+(?:\.\d+)+\s+','',label);tex.append(('\\subsection{' if level==3 else '\\section{')+tx(title)+'}');idx+=1;continue
 if line in ['@contents','@figures','@graphs','@tables']:
  event={'@contents':'TOCEntry','@figures':'FigureEntry','@graphs':'GraphEntry','@tables':'TableEntry'}[line];story.append(make_index(event));tex.append({'@contents':r'\tableofcontents','@figures':r'\listoffigures','@graphs':r'\noindent Graphs are listed with figures using the same figure numbering.','@tables':r'\listoftables'}[line]);idx+=1;continue
 if line.startswith(('@figure|','@chart|','@sample|')):
  typ,num,file,caption=line.split('|',3)
  name= file if typ=='@figure' else (file+'.png' if typ=='@chart' else 'application_report.png')
  if name=='methodology.svg':name='methodology_render.png'
  path=assets/name
  from PIL import Image as PILImage
  with PILImage.open(path) as im:iw,ih=im.size
  maxh=CH-55;scale=min(CW/iw,maxh/ih);img=Image(str(path),width=iw*scale,height=ih*scale)
  cap=Paragraph('Figure '+num+': '+esc(caption),S['caption']);cap.anchor='figure-'+num;cap.plain='Figure '+num+': '+caption;cap.list_kind='FigureEntry'
  if typ=='@chart':cap.graph_entry=True
  if ih*scale>CH*.65:story.append(PageBreak())
  story.append(KeepTogether([img,cap]));fig_inventory.append({'number':num,'caption':caption,'asset':name,'type':typ})
  if typ=='@chart':
   g=Paragraph('',S['caption']);g.anchor='graph-'+num;g.plain=cap.plain;g.list_kind='GraphEntry';story.append(g)
  tex.append(r'\begin{figure}[p]\centering\includegraphics[width=\linewidth,height=.82\textheight,keepaspectratio]{\detokenize{assets/'+name+r'}}\caption{'+tx(caption)+r'}\end{figure}')
  idx+=1;continue
 if line.startswith('$$'):
  raw=line.strip('$');expr=maths[raw];eqnum+=1
  from matplotlib.mathtext import math_to_image
  buf=io.BytesIO();math_to_image('$'+expr+'$',buf,dpi=190,format='png');buf.seek(0)
  from PIL import Image as PILImage
  with PILImage.open(buf) as im:iw,ih=im.size
  buf.seek(0);sc=min((CW-50)/iw,72/190);eq=Image(buf,width=iw*sc,height=ih*sc)
  tb=Table([[eq,Paragraph('('+chapter+'.'+str(eqnum)+')',S['cell'])]],colWidths=[CW-40,40]);tb.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(0,0),'CENTER'),('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8)]));story.append(tb);tex.append('\\begin{equation}'+expr+'\\end{equation}');idx+=1;continue
 if line.startswith('|'):
  rows=[]
  while idx<len(lines) and lines[idx].strip().startswith('|'):
   cells=[c.strip() for c in lines[idx].strip().strip('|').split('|')]
   if not all(re.fullmatch(r':?-+:?',c or '-') for c in cells):rows.append(cells)
   idx+=1
  n=len(rows[0]);maxlens=[max(len(row[j]) if j<len(row) else 0 for row in rows) for j in range(n)];weights=[max(12,min(70,x))**.6 for x in maxlens];widths=[CW*w/sum(weights) for w in weights]
  if n>=6:widths=[CW/n]*n
  data=[[Paragraph(inline(c),S['cellh'] if i==0 else S['cell']) for c in row] for i,row in enumerate(rows)]
  tb=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT');tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf0f2')),('LINEABOVE',(0,0),(-1,0),.6,colors.black),('LINEBELOW',(0,0),(-1,0),.4,colors.grey),('LINEBELOW',(0,-1),(-1,-1),.5,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
  if chapter!='0':
   table_counts[chapter]=table_counts.get(chapter,0)+1;num=chapter+'.'+str(table_counts[chapter]);title=captions.get(num,'Supporting implementation evidence');cap=Paragraph('Table '+num+': '+title,S['caption']);cap.keepWithNext=True;cap.anchor='table-'+num;cap.plain='Table '+num+': '+title;cap.list_kind='TableEntry';story.append(cap);table_inventory.append({'number':num,'caption':title})
  story.extend([tb,Spacer(1,9)])
  tex.append(r'\begin{longtable}{'+''.join('p{'+str(round(.92/n,3))+r'\linewidth}' for _ in range(n))+'}\n'+('\\caption{'+tx(captions.get(num,''))+'}\\\\\n' if chapter!='0' else ''))
  for row in rows:tex.append(' & '.join(tx(c) for c in row)+r'\\')
  tex.append(r'\end{longtable}');continue
 # Paragraph/list blocks retain readable academic prose.
 para=[line];idx+=1
 while idx<len(lines) and lines[idx].strip() and not lines[idx].strip().startswith(('#','@','|','$$')):
  if re.match(r'^\d+\. ',lines[idx].strip()):break
  para.append(lines[idx].strip());idx+=1
 text=' '.join(para)
 ref=re.match(r'^\[(\d+)\] ',text)
 if ref:
  p=Paragraph('<a name="ref-'+ref.group(1)+'"/>'+esc(text),S['ref']);story.append(p)
 elif re.match(r'^\d+\. ',text):story.append(Paragraph(inline(text),S['list']))
 else:story.append(Paragraph(inline(text),S['body']))
 tex.append(tx(text)+'\n')
tex.append(r'\end{document}')
(ROOT/'TrustFin_AI_Report_v2.tex').write_text('\n'.join(tex),encoding='utf-8')
output=ROOT/'TrustFin_AI_Report_v2.pdf'
doc=ReportDoc(str(output),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,title='TrustFin AI - Final Year Project Report - Draft v2',author='TrustFin AI Project Group')
frame=Frame(LEFT,BOTTOM,CW,CH,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
doc.addPageTemplates(PageTemplate(id='main',frames=[frame],onPageEnd=footer));doc.multiBuild(story,maxPasses=8)
(ROOT/'build'/'inventory.json').write_text(json.dumps({'figures':fig_inventory,'tables':table_inventory,'headings':heading_inventory},indent=2),encoding='utf-8')
print('Built',output,'with',len(fig_inventory),'figures and',len(table_inventory),'numbered tables')
