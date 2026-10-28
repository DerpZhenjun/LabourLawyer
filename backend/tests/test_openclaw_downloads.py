"""Content review failures must remain retryable and must not enable forms.

Run with the bundled artifact Python (pypdf); never calls the model.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('review_downloads',ROOT/'scripts/review-openclaw-downloads.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)

class DownloadReviewTests(unittest.TestCase):
    def test_whole_word_guide_with_application_appendix_is_not_blank_form(self):
        result=review.classify_word_text('劳动人事争议仲裁（劳动者申请立案）服务指南\n一、适用范围\n事项代码\n申请材料\n附录 仲裁申请书 申请人 请求事项 事实理由')
        self.assertEqual(result['kind'],'service_guide')
        result=review.classify_word_text('申请人申请仲裁涉及的文书参考模板目录\n仲裁申请书 证据目录\n申请人 请求 事实')
        self.assertEqual(result['kind'],'other')

    def test_advertised_blank_download_keeps_its_actual_filled_example_warning(self):
        text='仲裁申请书\n申请人：张X，19*年出生\n被申请人：XX\n请求事项：支付3275元\n事实：2012年入职'
        result=review.classify_word_text(text)
        self.assertEqual(result['form_state'],'filled_example')
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            folder=Path(tmp);entry={'file':'form.doc','kind':'blank','download_status':'downloaded','sha256':'actual'}
            review.save(folder/'task.json',{'status':{'fill_verified':False},'selected_guide':{'templates':[entry],'downloaded_files':[]}})
            with patch.object(review,'inspect_download',return_value=result):task=review.review_task(folder)
            actual=task['selected_guide']['templates'][0]
            self.assertEqual(actual['advertised_kind'],'blank');self.assertEqual(actual['kind'],'sample')
            self.assertFalse(task['status']['fill_verified'])

    def test_legacy_word_uses_absolute_artifact_paths_and_keeps_original(self):
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            folder=Path(tmp);source=folder/'application.doc';source.write_bytes(b'legacy-word-source')
            original=source.read_bytes()
            def word_inspect(args,**kwargs):
                text=Path(args[args.index('-Text')+1]);pdf=Path(args[args.index('-Pdf')+1])
                self.assertTrue(text.is_absolute());self.assertTrue(pdf.is_absolute())
                text.write_text('仲裁申请书 申请人 请求 事实','utf8');pdf.write_bytes(b'reference')
            with patch.object(review.subprocess,'run',side_effect=word_inspect):
                result=review.inspect_download(folder,{'file':'application.doc'})
            self.assertEqual(result['kind'],'application_form')
            self.assertEqual(source.read_bytes(),original)
            self.assertFalse(result['fill_verified'])

    def test_inconclusive_review_keeps_evidence_and_can_recover(self):
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            folder=Path(tmp)
            entry={'file':'download.pdf','download_status':'downloaded','sha256':'abc'}
            review.save(folder/'task.json',{'status':{'fill_verified':False},'selected_guide':{'templates':[entry],'downloaded_files':[{'sha256':'abc'}]}})
            with patch.object(review,'inspect_download',side_effect=TimeoutError('Ubuntu timeout')):
                result=review.review_task(folder)
            self.assertFalse(result['download_reviewed']);self.assertFalse(result['status']['template_downloaded'])
            self.assertEqual(result['pending_downloads'],['download.pdf'])
            self.assertTrue((folder/'task-before-download-review.json').is_file())
            with patch.object(review,'inspect_download',return_value={'kind':'service_guide','sha256':'abc'}):
                result=review.review_task(folder)
            self.assertTrue(result['download_reviewed']);self.assertEqual(result['pending_downloads'],[])
            self.assertEqual(result['selected_guide']['templates'],[])
            self.assertEqual(len(result['selected_guide']['supporting_documents']),1)
            self.assertFalse(result['status']['fill_verified'])

    def test_uncertain_cache_is_retried_but_successful_cache_is_reused(self):
        parent=ROOT/'.runtime/openclaw-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            folder=Path(tmp);path=folder/'form.docx'
            xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>仲裁申请书 申请人 请求 事实</w:t></w:r></w:p></w:body></w:document>'
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('word/document.xml',xml)
            digest=review.hashlib.sha256(path.read_bytes()).hexdigest();cache=folder/'download-reviews'/digest[:16]/'review.json'
            review.save(cache,{'kind':'uncertain','reason':'previous failure'})
            result=review.inspect_download(folder,{'file':'form.docx'})
            self.assertEqual(result['kind'],'application_form');self.assertFalse(result['fill_verified'])
            self.assertEqual(len(list(cache.parent.glob('review-previous-*.json'))),1)
            with patch.object(review.zipfile,'ZipFile',side_effect=AssertionError('Successful cache should be reused')):
                self.assertEqual(review.inspect_download(folder,{'file':'form.docx'}),result)

if __name__=='__main__':unittest.main()
