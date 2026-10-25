"""Process controls are stubbed: these checks never signal a running server."""
import importlib.util
from pathlib import Path
import signal
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('stop_dev', Path(__file__).with_name('stop-dev-server.py'))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
COMMAND = '.venv/bin/python -m uvicorn backend.api:app --host 127.0.0.1 --port 8011 --no-access-log --reload --reload-dir backend'


class StopDevTest(unittest.TestCase):
    def test_reload_parent_is_signalled_once_for_both_listeners(self):
        parent = (COMMAND, 1, '/release-worktree')
        with patch.object(server, 'listeners', side_effect=[{10, 11}, set()]), patch.object(server, 'repository', return_value='/same-repo'), patch.object(server, 'process', side_effect=lambda pid: parent if pid == 10 else ('python spawn_main', 10, '/release-worktree')), patch.object(server.os, 'kill') as kill:
            server.stop()
            kill.assert_called_once_with(10, signal.SIGTERM)

    def test_unrelated_listener_prevents_all_signals(self):
        with patch.object(server, 'listeners', return_value={10, 11}), patch.object(server, 'repository', return_value='/repo'), patch.object(server, 'process', side_effect=lambda pid: (COMMAND, 1, '/repo') if pid == 10 else ('python -m http.server 8011', 1, '/repo')), patch.object(server.os, 'kill') as kill:
            with self.assertRaises(RuntimeError): server.stop()
            kill.assert_not_called()

    def test_other_repository_or_production_port_is_rejected(self):
        for command, repo in [(COMMAND, '/other-repo'), (COMMAND.replace('8011', '8010'), '/repo')]:
            with self.subTest(command=command, repo=repo), patch.object(server, 'process', return_value=(command, 1, '/other')), patch.object(server, 'repository', return_value=repo):
                with self.assertRaises(RuntimeError): server.reload_server(10, '/repo')

    def test_changed_process_is_not_signalled(self):
        with patch.object(server, 'listeners', return_value={10}), patch.object(server, 'repository', return_value='/repo'), patch.object(server, 'process', side_effect=[(COMMAND, 1, '/repo'), ('other', 1, '/repo')]), patch.object(server.os, 'kill') as kill:
            with self.assertRaises(RuntimeError): server.stop()
            kill.assert_not_called()

    def test_empty_port_does_not_require_server_configuration(self):
        with patch.object(server, 'listeners', return_value=set()), patch.object(server.os, 'kill') as kill:
            server.stop()
            kill.assert_not_called()

    def test_timeout_never_force_kills(self):
        with patch.object(server, 'listeners', return_value={10}), patch.object(server, 'repository', return_value='/repo'), patch.object(server, 'process', return_value=(COMMAND, 1, '/repo')), patch.object(server.time, 'monotonic', side_effect=[0, 11]), patch.object(server.os, 'kill') as kill:
            with self.assertRaises(RuntimeError): server.stop()
            kill.assert_called_once_with(10, signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
