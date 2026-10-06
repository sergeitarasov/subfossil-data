import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import workflow as w


def row(choice='', views=(1,2)):
    return {'id': 1, 'catalogNumber': 'ROD-SF-head-1', 'bodyPart': 'head', 'imageToUse': choice,
            'images': [{'visible_name': f'View {v} - test.jpg', 'url': 'https://example.test/image'} for v in views]}


class SelectionTests(unittest.TestCase):
    def test_selection_contract(self):
        for choice, expected in [('View 1',1),('View 2',2),('Both',1),('',1),('Not decided',1)]:
            with self.subTest(choice=choice):
                self.assertEqual(w.select_view(row(choice))[2], expected)
        self.assertIsNone(w.select_view(row('Neither'))[0])
        self.assertEqual(w.select_view(row('',()))[1], 'missing_images')
        self.assertEqual(w.select_view(row('View 2',(1,)))[1], 'selected_view_missing')
        self.assertEqual(w.select_view(row('',(2,)))[2], 2)

    def test_order_independent_and_ambiguous(self):
        self.assertEqual(w.select_view(row('View 1',(2,1)))[0]['visible_name'], 'View 1 - test.jpg')
        self.assertEqual(w.select_view(row('',(1,1)))[1], 'ambiguous_views')
        r = row(); r['images'][0]['visible_name'] = 'unknown.jpg'
        self.assertEqual(w.select_view(r)[1], 'ambiguous_views')

    def test_path_traversal(self):
        for name in ['../head','head/other','/tmp/file','head\\other']:
            with self.assertRaises(ValueError): w.safe_name(name)


class CanvasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.run = self.vault/'runs'/'head_test'
        self.run.mkdir(parents=True)
        (self.run/'resized').mkdir()
        from PIL import Image
        Image.new('RGB',(600,300),'white').save(self.run/'resized'/'ROD-SF-head-1.jpg')
        w.write_json(self.run/'selection.json',[{'catalogNumber':'ROD-SF-head-1','file':'ROD-SF-head-1.jpg'}])

    def tearDown(self): self.tmp.cleanup()

    def test_label_image_mapping(self):
        with patch.object(w,'grid_layout',return_value=[{'x':0,'y':0}]):
            canvas=w.create_canvas(self.run,'head_test')
        self.assertEqual(len(canvas['nodes']),1)
        node=canvas['nodes'][0]
        self.assertEqual(node['type'],'file')
        self.assertEqual(Path(node['file']).stem,'ROD-SF-head-1')
        self.assertTrue((self.vault/node['file']).exists())
        self.assertEqual(node['width']/node['height'],2)
        self.assertNotIn('label',node)

    def prepare_publish(self):
        d=self.vault/'canvas'/'baserow';d.mkdir(parents=True)
        canvas={'nodes':[{'type':'file','file':'runs/head_test/resized/ROD-SF-head-1.jpg','x':12}]}
        w.write_json(d/'head_test.canvas',canvas)
        w.write_json(self.run/'generated.canvas',canvas)
        stage=self.vault/'runs'/'.staging-head_test'
        stage.mkdir()
        w.write_json(stage/'generated.canvas',{'nodes':[]})
        return stage,d,canvas

    def test_protect_species(self):
        stage,d,canvas=self.prepare_publish()
        w.write_json(self.vault/'canvas'/'species'/'sp1.canvas',canvas)
        with self.assertRaises(ValueError): w.publish_run(stage,self.vault,'head_test','overwrite')
        self.assertTrue(stage.exists())
        self.assertEqual(w.read_json(d/'head_test.canvas'),canvas)

    def test_archive_links(self):
        stage,d,canvas=self.prepare_publish()
        w.publish_run(stage,self.vault,'head_test','overwrite')
        old=next((self.vault/'archives').glob('*/head_test.canvas'))
        image=w.read_json(old)['nodes'][0]['file']
        self.assertTrue((self.vault/image).exists())
        self.assertTrue(image.startswith('archives/'))
        self.assertEqual(w.read_json(d/'head_test.canvas'),{'nodes':[]})

    def test_collision_no_overwrite(self):
        stage,d,canvas=self.prepare_publish()
        with self.assertRaises(ValueError): w.publish_run(stage,self.vault,'head_test','new')
        self.assertEqual(w.read_json(d/'head_test.canvas'),canvas)


class LayoutTests(unittest.TestCase):
    def test_small_prime_and_identical_collections(self):
        import numpy as np
        for n,identical in [(1,False),(2,False),(3,False),(7,False),(12,False),(7,True)]:
            with self.subTest(n=n,identical=identical), tempfile.TemporaryDirectory() as folder:
                p=Path(folder)
                names=[f'{i}.jpg' for i in range(n)]
                w.write_json(p/'selection.json',[{'file':name} for name in names])
                data=np.zeros((n,20)) if identical else np.random.default_rng(3).normal(size=(n,20))
                np.savez(p/'embeddings.npz',files=names,features=data)
                layout=w.grid_layout(p,42)
                self.assertEqual(len({(x['x'],x['y']) for x in layout}),n)
                self.assertLessEqual(max(x['x'] for x in layout),int(np.ceil(np.sqrt(n))))

class ApiTests(unittest.TestCase):
    def test_pagination_and_select_field_filtering(self):
        from argparse import Namespace
        a=Namespace(snapshot=None,baserow_url='https://example.test',table_id=672,body_part='head')
        arow=row();arow['bodyPart']={'value':'head'}
        other=row();other['bodyPart']='elytra'
        responses=[[{'name':n} for n in ['catalogNumber','bodyPart','images','imageToUse']],
                   {'results':[other],'next':'second'}, {'results':[arow],'next':None}]
        with patch.dict('os.environ',{'BASEROW_TOKEN':'test'}), patch.object(w,'api_json',side_effect=responses) as api:
            self.assertEqual(w.fetch_rows(a),[arow])
            self.assertIn('page=2',api.call_args_list[-1].args[0])

class DownloadTests(unittest.TestCase):
    def test_camera_filename_spaces_and_stored_name_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/'2026-10-06 ZS PMax.jpg').write_bytes(b'visible')
            im={'visible_name':'2026-10-06 ZS PMax.jpg','name':'stored.jpg'}
            w.download_image(im,p/'out.jpg',p)
            self.assertEqual((p/'out.jpg').read_bytes(),b'visible')
            (p/'stored.jpg').write_bytes(b'unique')
            w.download_image(im,p/'out.jpg',p)
            self.assertEqual((p/'out.jpg').read_bytes(),b'unique')

    def test_single_new_camera_filename(self):
        r=row('View 1',(1,));r['images'][0]['visible_name']='2026-10-06 ZS PMax.jpg'
        self.assertEqual(w.select_view(r)[2],1)
        r['imageToUse']='View 2'
        self.assertIsNone(w.select_view(r)[0])

if __name__ == '__main__': unittest.main()
