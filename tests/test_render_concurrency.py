"""New-video and resume must refuse to start a second concurrent render.

3D rendering is GPU-bound; two live jobs on one machine thrash each other and
leave half-finished projects. These tests drive the Flask routes with the job
table pre-seeded, so no real render or thread runs.
"""
import time
import unittest

import app as app_module
import projects_mgr


class ConcurrencyGuardTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        app_module.JOBS.clear()

    def tearDown(self):
        app_module.JOBS.clear()

    def _mark_running(self, project="project-busy"):
        app_module.JOBS["busy-job"] = {
            "state": "running", "project": project,
            "progress_updated_at": time.time(), "stage": "render",
            "message": "3D render line 5/10",
        }

    def test_active_render_detects_fresh_running_job(self):
        self._mark_running()
        busy = app_module._active_render()
        self.assertIsNotNone(busy)
        self.assertEqual(busy["project"], "project-busy")

    def test_active_render_ignores_stale_job(self):
        app_module.JOBS["old"] = {
            "state": "running", "project": "p",
            "progress_updated_at": time.time() - projects_mgr.STALE_JOB_SECONDS - 10,
        }
        self.assertIsNone(app_module._active_render())

    def test_active_render_can_exclude_a_project(self):
        self._mark_running("project-busy")
        self.assertIsNone(app_module._active_render(exclude_project="project-busy"))

    def test_new_video_refused_while_a_render_runs(self):
        self._mark_running()
        resp = self.client.post("/api/generate", json={
            "script": "[Scene: X]\nAli: (happy) Hello dosto kaise ho aaj."})
        self.assertEqual(resp.status_code, 409)
        body = resp.get_json()
        self.assertIn("busy_project", body)
        self.assertEqual(body["busy_project"], "project-busy")

    def test_new_video_allowed_when_idle(self):
        # Stub the builder so no real render/network runs; we only assert the
        # guard lets the request through and a job is created.
        from unittest import mock
        with mock.patch.object(app_module.builder, "build",
                               return_value={"video": "x", "proj": "p"}):
            resp = self.client.post("/api/generate", json={
                "script": "[Scene: X]\nAli: (happy) Hello dosto kaise ho aaj."})
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json()
            self.assertIn("job_id", body)
            # let the daemon thread finish against the stub
            for _ in range(50):
                job = app_module.JOBS.get(body["job_id"], {})
                if job.get("state") in {"done", "error", "stopped"}:
                    break
                time.sleep(0.02)
        # clean up the stub project dir this route created
        import shutil, os
        import config
        stub = os.path.join(config.PROJECTS_DIR, body.get("project", ""))
        if body.get("project") and os.path.isdir(stub):
            shutil.rmtree(stub, ignore_errors=True)


class ScriptReconstructionTests(unittest.TestCase):
    def test_script_from_parsed_single_source(self):
        parsed = {"scenes": [{"location": "Jungle", "lines": [
            {"speaker": "Ali", "emotion": "happy", "text": "Chalo"},
            {"speaker": "Sara", "emotion": "neutral", "text": "Theek"},
        ]}]}
        text = projects_mgr.script_from_parsed(parsed)
        self.assertEqual(text, "[Scene: Jungle]\nAli: (happy) Chalo\nSara: Theek")

    def test_empty_parsed_is_safe(self):
        self.assertEqual(projects_mgr.script_from_parsed({}), "")
        self.assertEqual(projects_mgr.script_from_parsed(None), "")


if __name__ == "__main__":
    unittest.main()
