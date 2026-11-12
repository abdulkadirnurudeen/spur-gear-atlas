"""Build independent static pages from the maintained atlas content template."""
from pathlib import Path
import html,json,re
P=Path(__file__).resolve().parents[1];source=(P/'src/atlas-content.html').read_text();version=json.loads((P/'package.json').read_text())['version']
source=source.replace('0.3.1',version)
main=source.index('<main id="top">');design=source.index('  <section class="section wrap design-section"');explore=source.index('  <section class="section wrap" id="explore"');research=source.index('  <section class="section wrap research-index"');carbon=source.index('  <section class="carbon-section"');evidence=source.index('  <section class="section wrap" id="evidence"');about=source.index('  <section class="about-section"') if '  <section class="about-section"' in source else source.index('  <section class="about-section wrap"')
end=source.index('</main>');foot=source.index('<footer');dialog=source.index('<dialog');toast=source.index('<div id="toast"')
prefix=source[:main];footer=source[foot:dialog];modal=source[dialog:toast];ending=source[toast:]
parts={'home':source[main+len('<main id="top">'):design],'design':source[design:explore],'explore':source[explore:carbon],'carbon':source[carbon:evidence],'evidence':source[evidence:about],'about':source[about:end]}
pages={'home':('index.html','Home'),'design':('design.html','Design check'),'explore':('explore.html','Explore'),'carbon':('carbon.html','Carbon payback'),'evidence':('evidence.html','Evidence & methods'),'about':('about.html','About')}
descriptions={'home':'SpurAtlas: choose a design comparison, inspect documented gear evidence, review carbon scenarios and find the supporting methods.','design':'Choose assessed gear and load options, rank compatible perforations and export a reproducible engineering decision record.','explore':'Inspect ten retained test layouts and the wider source-linked research index across nine tooth counts.','carbon':'Review the original manufacturing-carbon scenarios for two documented 40-tooth gear cases.','evidence':'Read the power-law-based retention models, model comparisons, mesh assessments and numerical evidence behind SpurAtlas.','about':'SpurAtlas authorship, scientific scope, citations, supporting research releases and reuse information.'}
links={'design':'design.html','explore':'explore.html','research-index':'explore.html#research-index','carbon':'carbon.html','evidence':'evidence.html','about':'about.html'}
cards=[('design','Design check','Choose assessed gear and load options, compare compatible openings and save a decision record.'),('explore','Explore the records','Inspect ten reference layouts and 631 traceable response records across nine tooth counts.'),('carbon','Carbon payback','Review the 48 original manufacturing and service scenarios for two 40-tooth cases.'),('evidence','Evidence & methods','Inspect the equations, prediction errors, field examples and numerical-resolution checks.'),('about','About & citation','Find the author, supporting research releases, scientific scope and reuse information.')]
homecards='<section class="wrap home-pages" aria-labelledby="home-pages-title"><span class="section-number">CHOOSE A PAGE</span><h2 id="home-pages-title">Find the evidence for your decision.</h2><div class="page-card-grid">'+''.join(f'<a class="page-card" href="{pages[key][0]}"><span class="card-index">{i:02}</span><h3>{html.escape(title)}</h3><p>{html.escape(copy)}</p><span class="page-card-link">Open {html.escape(pages[key][1])} →</span></a>' for i,(key,title,copy) in enumerate(cards,1))+'</div></section>'
for key,(filename,title) in pages.items():
 head=prefix.replace('<body>',f'<body data-page="{key}">').replace('href="#top" class="brand"','href="index.html" class="brand"').replace('href="#explore">Skip to the atlas','href="#top">Skip to page content')
 head=re.sub(r'<title>.*?</title>',f'<title>{html.escape(title)} — SpurAtlas</title>',head)
 head=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="{html.escape(descriptions[key],quote=True)}">',head)
 for anchor,url in links.items():head=head.replace(f'href="#{anchor}"',f'href="{url}"')
 if key!='home':head=head.replace(f'href="{filename}">',f'href="{filename}" aria-current="page">')
 content=parts[key]
 for anchor,url in links.items():
  if not (key=='explore' and anchor=='research-index'):content=content.replace(f'href="#{anchor}"',f'href="{url}"')
 if key=='home':content+=homecards
 else:
  first={'design':'design-title','explore':'explore-title','carbon':'carbon-title','evidence':'evidence-title','about':'about-title'}[key]
  content=re.sub(rf'<h2 id="{first}">(.*?)</h2>',rf'<h1 id="{first}">\1</h1>',content,flags=re.S)
 if key=='evidence':content=content.replace('the 42- and 46-tooth explorer layouts above','the 42- and 46-tooth layouts on the Explore page')
 return_link='' if key=='design' else '<a id="current-design-link" class="subtle-link" href="design.html">Start a design comparison</a>'
 trail='' if key=='home' else f'<div class="wrap page-trail"><div><a href="index.html">Home</a><span aria-hidden="true"> / </span><span>{html.escape(title)}</span></div>{return_link}</div>'
 if key=='carbon':trail+='<div class="wrap linked-design-note"><p>These are the original two 40-tooth case studies. For the geometry selected in your design comparison, <a href="design.html#matched-carbon-panel">open its matched carbon calculation</a>.</p></div>'
 error='<div class="wrap page-error" id="page-error" role="alert" hidden><p>The research data could not be loaded. Reload this page or use the supporting source record.</p><button id="page-retry" class="button ghost small">Reload page</button></div>'
 output=head+'<main id="top" tabindex="-1">'+trail+error+content+'</main>\n'+footer+(modal if key=='evidence' else '')+ending
 (P/'dist'/filename).write_text(output)
print(json.dumps({'pages':[v[0] for v in pages.values()],'version':version}))
