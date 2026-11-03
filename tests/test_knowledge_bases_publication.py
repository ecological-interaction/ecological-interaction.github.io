"""AMRKB/BIPKB pinned imports, scientific preservation and deployment boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from markdown import markdown as render
from mkdocs.exceptions import ConfigurationError
import yaml
from scripts import knowledge_bases_publication as p

class KnowledgeBasePublicationTests(unittest.TestCase):
    def page(self,name,science=False):
        return SimpleNamespace(file=SimpleNamespace(src_uri=f'information/{name}/'+('scientific-reference-register.md' if science else 'index.md')))
    def test_manifest_rejects_floating_refs_wrong_repositories_and_incomplete_allowlists(self):
        for name in p.PROJECTS:
            original=p.manifest(name)
            for change in [{'commit':'main'},{'repository':'https://example.org'},{'documents':[]},{'assets':[]},{'references':[]}]:
                with self.subTest(name=name,change=change),patch.object(Path,'read_text',return_value=json.dumps(original|change)):
                    with self.assertRaises(ConfigurationError):p.manifest(name)
            bad=copy.deepcopy(original);bad['assets'][0]['sha256']='invalid'
            with patch.object(Path,'read_text',return_value=json.dumps(bad)):
                with self.assertRaises(ConfigurationError):p.manifest(name)
    def test_missing_modified_or_floating_source_fails_closed(self):
        for code in [0,128]:
            with patch.object(p.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=b'corrupt')):
                with self.assertRaises(ConfigurationError):p.read_file('missing','a'*40,{'source':'README.md','sha256':'0'*64})
        with self.assertRaises(ConfigurationError):p.read_file('missing','main',{})
    def test_hosted_sources_and_collisions(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'},clear=True):
            with self.assertRaises(ConfigurationError):p.on_files([],SimpleNamespace())
        with patch.dict(os.environ,{},clear=True):
            for name in p.PROJECTS:
                for item in p.manifest(name)['documents']+p.manifest(name)['assets']:
                    with self.assertRaises(ConfigurationError):p.on_files([SimpleNamespace(src_uri=item['page'])],SimpleNamespace())
    def test_real_pins_references_and_byte_identical_svg_imports(self):
        expected={'AMRKB':'e8dd2592e57df15ff21f7d7d69c8960a75d61a24','BIPKB':'450efb895a9db28ea715f6ce28eb031f6a1dfe68'}
        generated={}
        with patch.object(p.File,'generated',side_effect=lambda config,path,**kw:generated.setdefault(path,kw['content'])):p.on_files([],SimpleNamespace())
        self.assertEqual(len(generated),7)
        for name in p.PROJECTS:
            data=p.manifest(name);self.assertEqual(data['commit'],expected[name])
            for key in ['documents','references','assets']:
                for item in data[key]:
                    raw=p.read_file(p.source_checkout(name),data['commit'],item)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
                    if key=='assets':
                        self.assertEqual(raw,generated[item['page']]);self.assertIn('viewBox',ET.fromstring(raw).attrib)
                    elif key=='documents':self.assertEqual(raw.decode(),generated[item['page']])
            self.assertNotIn(f'information/{name}/research-protocol.md',generated)
            self.assertNotIn(f'information/{name}/machine-reference.md',generated)
    def test_research_tables_and_record_coverage_preserved(self):
        import re
        for name in p.PROJECTS:
            data=p.manifest(name)
            for item in data['documents']:
                original=p.read_file(p.source_checkout(name),data['commit'],item).decode()
                result=p.on_page_markdown(original,SimpleNamespace(file=SimpleNamespace(src_uri=item['page'])))
                self.assertEqual([l for l in original.splitlines() if l.startswith('|')],[l for l in result.splitlines() if l.startswith('|')])
                self.assertIn(p.source_url(data,name+'_Machine_Reference.json'),result)
                if item['source']=='README.md':
                    self.assertIn('](scientific-reference-register.md)',result)
                    for asset in data['assets']:self.assertIn(']('+asset['source']+')',result)
                elif name=='AMRKB':
                    index=result.split('## Complete candidate identity index',1)[1].split('\n## ',1)[0]
                    self.assertEqual(len(set(re.findall(r'^\| (AMRKB-REC-\d+) \|',index,re.M))),292)
                else:self.assertEqual(len(set(re.findall(r'<a id="(bipkb-a1-[a-z]\d{3})"',result))),293)
    def test_duplicate_heading_aliases_target_correct_sections(self):
        d=p.manifest('AMRKB');text=p.read_file(p.source_checkout('AMRKB'),d['commit'],d['documents'][1]).decode();result=p.on_page_markdown(text,self.page('AMRKB',True));html=render(result,extensions=['toc','tables','fenced_code'])
        for anchor in ['nutrient-management-2','crop-organisation-2','tree-integration-1','livestock-integration-1']:self.assertEqual(html.count(f'id="{anchor}"'),1)
        self.assertIn('<a id="nutrient-management-2"></a>\n\n### Nutrient management',result)
    def test_compatibility_aliases_do_not_hide_page_titles(self):
        text='# BIPKB — Bioindicators and Phenotypes Knowledge Base\n\nBody.\n'
        result=p.compatibility_anchors(text)
        self.assertTrue(result.startswith('# BIPKB — Bioindicators and Phenotypes Knowledge Base\n'))
        self.assertIn('<a id=',result)
    def test_code_provenance_is_untouched_and_unapproved_links_fail(self):
        d=p.manifest('AMRKB');text='`[Source](AMRKB_Machine_Reference.json)`\n\n```md\n[Source](unapproved.md)\n```\n'
        self.assertEqual(p.map_links(text,'AMRKB',d),text)
        with self.assertRaises(ConfigurationError):p.map_links('[Unexpected](../../private.md)','AMRKB',d)
    def test_other_pages_unchanged_and_overview_links_are_scoped(self):
        text='# Existing source\n';page=SimpleNamespace(file=SimpleNamespace(src_uri='information/EIRKB/index.md'));self.assertEqual(p.on_page_markdown(text,page),text)
        page.file.src_uri='information/index.md';result=p.on_page_markdown(text,page);self.assertTrue(result.startswith(text))
        for name in p.PROJECTS:self.assertIn(f'({name}/index.md)',result)
    def test_navigation_and_anonymous_workflow_preserve_deployment(self):
        c=yaml.safe_load((p.ROOT/'mkdocs.yml').read_text());info=c['nav'][1]['Information']
        w=yaml.load((p.ROOT/'.github/workflows/deploy.yml').read_text(),Loader=yaml.BaseLoader);self.assertEqual(w['on']['push']['branches'],['main']);steps=w['jobs']['deploy']['steps']
        for name in p.PROJECTS:
            section=next(x[p.PROJECTS[name]['label']] for x in info if isinstance(x,dict) and p.PROJECTS[name]['label'] in x)
            self.assertEqual(section,[f'information/{name}/index.md',{'Scientific Reference':f'information/{name}/scientific-reference-register.md'}])
            fetch=next(s for s in steps if s.get('name')==f'Retrieve approved {name} commit anonymously');self.assertEqual(fetch['env']['GIT_CONFIG_GLOBAL'],'/dev/null');self.assertEqual(fetch['env']['GIT_TERMINAL_PROMPT'],'0');self.assertIn('"credential.helper="',fetch['run']);self.assertIn('"--depth=1"',fetch['run'])
            for stepname in ['Test publication import','Build website']:self.assertIn(name+'_SOURCE',next(s for s in steps if s.get('name')==stepname)['env'])
        self.assertTrue(any(s.get('uses','').startswith('actions/deploy-pages@') for s in steps))
    def test_hook_loads_without_repository_python_path(self):
        import subprocess,sys,tempfile
        script="from mkdocs.config import load_config; import sys; c=load_config(sys.argv[1]); assert any(h.__file__.endswith('knowledge_bases_publication.py') for h in c['hooks'].values())"
        with tempfile.TemporaryDirectory() as directory:result=subprocess.run([sys.executable,'-I','-B','-c',script,str(p.ROOT/'mkdocs.yml')],cwd=directory,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
