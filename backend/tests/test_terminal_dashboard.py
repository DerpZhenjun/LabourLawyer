import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import terminal_progress as progress
spec=importlib.util.spec_from_file_location('terminal_dashboard',ROOT/'scripts/terminal-dashboard.py')
dashboard=importlib.util.module_from_spec(spec);spec.loader.exec_module(dashboard)


class TerminalDashboardTests(unittest.TestCase):
    def test_chinese_width_and_control_sequences_do_not_break_columns(self):
        text=dashboard.fit('\x1b[31m北京市\x1b[0m\r\n',12)
        self.assertEqual(dashboard.cells(text),12)
        self.assertNotIn('\x1b',text);self.assertNotIn('\n',text)
        view=dashboard.View('TEST');view.regions={str(i):'historical' for i in range(31)}
        for width,height in ((44,24),(80,30),(120,36)):
            lines=view.render(width,height).splitlines()
            self.assertLessEqual(len(lines),height)
            self.assertTrue(all(dashboard.cells(line)==width for line in lines))

    def test_reader_retains_partial_utf8_and_ignores_malformed_lines(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            path=Path(temp)/'events.jsonl';reader=dashboard.Journal(path)
            data=json.dumps({'message':'中文'},ensure_ascii=False).encode()+b'\n'
            path.write_bytes(data[:14]);self.assertEqual(reader.poll(),[])
            with path.open('ab') as f:f.write(data[14:]+b'bad json\n')
            self.assertEqual(reader.poll(),[{'message':'中文'}])
            self.assertEqual(reader.poll(),[])

    def test_one_model_completion_does_not_hide_another_waiting_call(self):
        view=dashboard.View('TEST')
        for key in ('a','b'):view.apply({'phase':'model','state':'waiting','call_id':key,'at':0,'timeout_seconds':180})
        view.apply({'phase':'model','state':'completed','call_id':'a'})
        self.assertEqual(set(view.waits),{'b'});self.assertEqual(view.model_ok,1)
        view.apply({'phase':'model','state':'running','call_id':'b'})
        self.assertEqual(set(view.waits),{'b'})
        view.apply({'phase':'model','state':'failed','call_id':'b'})
        self.assertFalse(view.waits);self.assertEqual(view.model_failed,1)

    def test_processed_is_not_success_and_zero_exit_does_not_hide_incomplete(self):
        view=dashboard.View('TEST');view.regions={'ningxia':'step_limit'}
        self.assertEqual(dashboard.finish_state(view,0),'complete_with_gaps')
        view.state='review_incomplete'
        self.assertEqual(dashboard.finish_state(view,0),'review_incomplete')
        self.assertEqual(dashboard.finish_state(view,1),'failed')
        view.state='running';view.regions={'ningxia':'acquired'}
        self.assertEqual(dashboard.finish_state(view,0),'complete')
        view.regions={'ningxia':'pending'}
        self.assertEqual(dashboard.finish_state(view,0),'incomplete')

    def test_gateway_wait_is_separate_from_remote_inference_and_clears(self):
        view=dashboard.View('TEST')
        view.apply({'phase':'browser','state':'waiting','timeout_seconds':45,'at':dashboard.time.time()})
        self.assertIn('BROWSER WAIT',view.render())
        self.assertFalse(view.waits)
        view.apply({'phase':'browser','state':'running','message':'ready'})
        self.assertIsNone(view.operation_wait)
        view.apply({'phase':'browser','state':'waiting','timeout_seconds':40})
        view.apply({'phase':'job','state':'failed'})
        self.assertIsNone(view.operation_wait)

    def test_windows_stop_falls_back_to_owned_process_on_taskkill_timeout(self):
        process=Mock(pid=123,returncode=None);process.poll.return_value=None
        process.wait.side_effect=[dashboard.subprocess.TimeoutExpired('worker',5),0]
        with patch.object(dashboard.os,'name','nt'):
            with patch.object(dashboard.subprocess,'run',side_effect=dashboard.subprocess.TimeoutExpired('taskkill',10)) as killtree:
                warning=dashboard.stop_worker(process)
        process.kill.assert_called_once()
        self.assertEqual(killtree.call_args.args[0],['taskkill','/PID','123','/T','/F'])
        self.assertIn('子进程树',warning)

    def test_stop_does_not_signal_an_already_finished_process(self):
        process=Mock();process.poll.return_value=0
        self.assertEqual(dashboard.stop_worker(process),'')
        process.send_signal.assert_not_called();process.kill.assert_not_called()

    def test_completed_observed_job_clears_waiting_and_old_browser_step(self):
        view=dashboard.View('TEST')
        view.apply({'phase':'browser','step':3,'max_steps':12})
        view.apply({'phase':'model','state':'waiting','call_id':'one'})
        self.assertTrue(view.waits)
        view.apply({'phase':'job','state':'interrupted'})
        self.assertFalse(view.waits);self.assertIsNone(view.step)

    def test_emitter_is_optional_and_logging_failure_does_not_fail_job(self):
        token=progress._path.set(None)
        try:
            with patch.dict(os.environ,{progress.ENV:''}):
                self.assertFalse(progress.emit('capture',message='test'))
            with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
                blocker=Path(temp)/'file';blocker.write_text('not directory')
                with patch.dict(os.environ,{progress.ENV:str(blocker/'events.jsonl')}):
                    self.assertFalse(progress.emit('capture',message='test'))
        finally:progress._path.reset(token)

    def test_default_job_channel_changes_without_polluting_server_environment(self):
        token=progress._path.set(None)
        try:
            with patch.dict(os.environ,{progress.ENV:''}):
                with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
                    first,second=Path(temp)/'one',Path(temp)/'two'
                    progress.configure(first);progress.emit('job',message='one')
                    progress.configure(second);progress.emit('job',message='two')
                    self.assertEqual(dashboard.Journal(first/'progress.jsonl').poll()[0]['message'],'one')
                    self.assertEqual(dashboard.Journal(second/'progress.jsonl').poll()[0]['message'],'two')
                    self.assertEqual(os.environ[progress.ENV],'')
        finally:progress._path.reset(token)

    def test_external_cli_channel_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            path=Path(temp)/'external.jsonl'
            with patch.dict(os.environ,{progress.ENV:str(path)}):
                progress.configure(Path(temp)/'nested')
                progress.emit('capture',message='same channel')
                self.assertEqual(len(dashboard.Journal(path).poll()),1)
                self.assertFalse((Path(temp)/'nested/progress.jsonl').exists())
                self.assertEqual(dashboard.read_json(Path(temp)/'nested/terminal-progress.json')['events'],str(path))
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    dashboard.watch(plain=True,once=True,batch=Path(temp)/'nested')
                self.assertIn('same channel',output.getvalue())

    def test_saved_subset_keeps_its_scope_and_missing_journal_is_not_running(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            folder=Path(temp)
            dashboard.save(folder/'status.json',{'state':'complete_with_gaps','total':1,'completed':1,'requested_provinces':['ningxia']})
            dashboard.save(folder/'results.json',{'ningxia':{'state':'stalled'}})
            view=dashboard.saved_batch(folder)
            self.assertEqual((view.current,view.total),(1,1));self.assertTrue(view.saved)
            self.assertEqual(view.regions,{'ningxia':'stalled'})
            with contextlib.redirect_stdout(io.StringIO()) as output:dashboard.watch(plain=True,once=True,batch=folder)
            self.assertIn('COMPLETE_WITH_GAPS',output.getvalue());self.assertIn('指定任务范围',output.getvalue())

    def test_published_summary_does_not_switch_to_an_active_worker(self):
        with patch.object(dashboard,'active_journal',return_value=(0,Path('unused.jsonl'),'OTHER WORKER')):
            with contextlib.redirect_stdout(io.StringIO()) as output:dashboard.watch(plain=True,once=True)
            self.assertIn('PUBLISHED RESULTS',output.getvalue());self.assertNotIn('OTHER WORKER',output.getvalue())

    def test_monitor_exit_does_not_launch_or_stop_the_worker(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            folder=Path(temp)
            dashboard.save(folder/'status.json',{'state':'running','total':1,'completed':0})
            before=(folder/'status.json').read_bytes()
            with patch.object(dashboard.time,'sleep',side_effect=KeyboardInterrupt),patch.object(dashboard.subprocess,'Popen') as launch,patch.object(dashboard,'stop_worker') as stop:
                with contextlib.redirect_stdout(io.StringIO()):code=dashboard.watch(plain=True,batch=folder)
            self.assertEqual(code,0);launch.assert_not_called();stop.assert_not_called()
            self.assertEqual(before,(folder/'status.json').read_bytes())

    def test_identical_live_frame_is_not_redrawn_or_fully_cleared(self):
        screen=object.__new__(dashboard.Screen);screen.live=True;screen.last_frame=None
        view=dashboard.View('TEST')
        with patch.object(dashboard.time,'time',return_value=view.started),patch.object(dashboard.shutil,'get_terminal_size',return_value=os.terminal_size((100,36))):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                screen.draw(view);first=output.getvalue();screen.draw(view)
                self.assertEqual(first,output.getvalue())
                self.assertNotIn('\x1b[2J',first)

    def test_durable_province_task_overrides_older_partial_result(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            folder=Path(temp)
            dashboard.save(folder/'status.json',{'state':'complete_with_gaps','completed':2,'total':2,'requested_provinces':['hebei','ningxia']})
            dashboard.save(folder/'results.json',{'hebei':{'state':'stalled'}})
            dashboard.save(folder/'hebei/task.json',{'state':'acquired','status':{'guide_found':True}})
            dashboard.save(folder/'ningxia/task.json',{'state':'stalled','status':{'guide_found':False}})
            view=dashboard.saved_batch(folder)
            self.assertEqual(view.regions,{'hebei':'acquired','ningxia':'stalled'})
            self.assertEqual(view.counts,{'acquired':1,'gap':1})

    def test_real_child_logs_and_incomplete_exit_are_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            folder=Path(temp);worker=folder/'worker.py'
            worker.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT/'backend'))+')\nfrom terminal_progress import emit\nprint("真实子进程日志",flush=True)\nemit("job","review_incomplete",message="保留断点",error="test incomplete")\n','utf8')
            with patch.object(dashboard,'RUNTIME',folder/'runs'):
                with contextlib.redirect_stdout(io.StringIO()):code=dashboard.run([sys.executable,str(worker)],'TEST / INCOMPLETE',plain=True)
            self.assertEqual(code,1)
            run=next((folder/'runs').iterdir())
            self.assertIn('真实子进程日志',(run/'worker.log').read_text('utf8'))
            self.assertEqual(dashboard.read_json(run/'session.json')['state'],'review_incomplete')
            self.assertEqual(dashboard.Journal(run/'events.jsonl').poll()[-1]['state'],'review_incomplete')


if __name__=='__main__':unittest.main()
