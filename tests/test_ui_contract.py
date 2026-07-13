import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import app as app_module


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
CSS = ROOT / "static" / "css" / "studio.css"
JS = ROOT / "static" / "js" / "studio.js"
ICONS = ROOT / "static" / "icons" / "icons.svg"
FAVICON = ROOT / "static" / "icons" / "favicon.svg"

REQUIRED_IDS = {
    "aspectSeg", "cap_enabled", "cap_hl", "cap_perspk", "cap_size",
    "cap_words", "charList", "chGender", "chName", "chPhrase", "chTrait",
    "costEst", "edge_voice_group", "eleven_voice_group", "eleven_voice_status",
    "elevenlabs_voice_id", "epBox", "epGenBtn", "epHistory", "epIdea",
    "epLenSeg", "epMsg", "errMsg", "fast_preview", "ffGenBtn", "ffGenre",
    "ffIdea", "ffLang", "ffLenSeg", "ffMsg", "ffPro", "fps", "genBtn",
    "genCard", "gpu_encode", "hlSeg", "intro_on", "lfGenBtn", "lfGenre",
    "lfIdea", "lfLang", "lfMinSeg", "lfMsg", "lfOutline", "modeSeg",
    "motionSeg", "multiChar", "music_volume", "newSeriesBox", "pkgPanel",
    "posSeg", "previewBtn", "previewCard", "progressCard", "projCardTop",
    "projCount", "projList", "provStatus", "pvChars", "pvGenBtn", "pvScenes",
    "pvTitle", "quality", "rDownload", "refresh_eleven_voices", "render_engine",
    "resultCard", "resumeCard", "resumeList", "rTitle", "rVideo", "script",
    "scriptCard", "scriptFeedback", "scriptTabs", "serCast", "serGenre",
    "serInfo", "serLang", "serName", "serPremise", "serSel", "steps",
    "stopBtn", "storySeg", "style", "test_img", "testBtn", "testResult",
    "tplChars", "tplGenBtn", "tplGrid", "tplLang", "tplLenSeg", "tplMsg",
    "tplName", "tplPanel", "tplTopic", "tts_provider", "urdu_accent",
    "vignette", "voice_volume",
}

REQUIRED_ENDPOINT_MARKERS = {
    "/api/options", "/api/voices/elevenlabs", "/api/characters3d/validation",
    "/api/story-templates", "/api/characters", "/api/story-templates/generate",
    "/api/freeform", "/api/longform", "/api/characters-lib", "/api/series",
    "/api/suggest-style", "/api/analyze", "/api/improve", "/api/metadata",
    "/api/costumes", "/api/accessories", "/api/held", "/api/preview",
    "/api/resumable", "/api/projects", "/api/project/", "/api/resume/",
    "/api/generate", "/api/status/", "/api/stop/", "/api/test-runware",
    "/projects/",
}

REQUIRED_FUNCTIONS = {
    "load", "loadLib", "loadTemplates", "collectSettings", "preview",
    "renderPreview", "collectEditedParsed", "generate", "confirmGenerate",
    "startJob", "poll", "stopJob", "showResult", "showErr", "checkResumable",
    "loadProjectsList", "openProject", "playProject", "delProject",
    "resumeProject", "genFreeform", "genLongform", "genFromTemplate",
    "analyzeScript", "improveScript", "genPackage", "testRunware",
    "loadElevenLabsVoices", "syncVoiceProviderUI",
}

REQUIRED_SETTING_KEYS = {
    "style", "aspect", "quality", "fps", "fast_preview", "motion_preset",
    "render_mode", "story_mode", "multi_char", "render_engine", "gpu",
    "vignette", "subtitles_on", "intro_on", "outro_on", "tts_provider",
    "urdu_accent", "elevenlabs_voice_id", "voice_volume", "music_volume",
    "enabled", "words_per_group", "font_size", "position", "highlight_color",
    "highlight_style", "per_speaker_color",
}

REQUIRED_ICON_IDS = {
    "icon-studio", "icon-dashboard", "icon-create", "icon-characters",
    "icon-projects", "icon-templates", "icon-assets", "icon-settings",
    "icon-help", "icon-chevron-down", "icon-close", "icon-play", "icon-stop",
    "icon-download", "icon-folder", "icon-trash", "icon-sparkles",
    "icon-script", "icon-preview", "icon-volume", "icon-captions", "icon-render",
}

PHASE_TWO_IDS = {
    "studioShell", "workspace", "currentProjectName", "autosaveStatus",
    "resumeNotice", "resumeNoticeCount", "providerButton", "providerPopover",
    "helpButton", "helpPopover", "inspectorToggle", "contextInspector",
    "inspectorTitle", "workflowStepper", "view-dashboard", "view-create",
    "view-characters", "view-projects", "view-templates", "view-assets",
    "view-settings", "castEmptyState", "scriptCount", "summaryStoryMode",
    "summaryFormat", "summaryVoice", "summarySubtitles", "renderSceneCount",
    "renderCharacterCount", "renderQuality", "renderEngineSummary",
    "castInspectorCharacter", "castInspectorVoice", "castInspectorEmotion",
    "castInspectorAction", "castInspectorBackground",
}


class UIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")

    def test_presentation_is_externalized_without_duplicate_active_blocks(self):
        self.assertIn("url_for('static', filename='css/studio.css')", self.template)
        self.assertIn("url_for('static', filename='js/studio.js')", self.template)
        self.assertIn("url_for('static', filename='icons/favicon.svg')", self.template)
        self.assertIn("?v=20260713-phase1", self.template)
        self.assertIsNone(re.search(r"<style\b", self.template, re.IGNORECASE))
        self.assertIsNone(re.search(
            r"<script(?![^>]*\bsrc=)[^>]*>", self.template, re.IGNORECASE))
        self.assertGreater(len(self.css), 6_000)
        self.assertGreater(len(self.js), 40_000)

    def test_all_baseline_dom_ids_are_preserved_and_unique(self):
        ids = re.findall(r'\bid=["\']([^"\']+)["\']', self.template)
        self.assertEqual(len(ids), len(set(ids)), "Duplicate static DOM IDs found")
        self.assertTrue(REQUIRED_IDS.issubset(set(ids)),
                        f"Missing DOM IDs: {sorted(REQUIRED_IDS - set(ids))}")

    def test_browser_functions_and_endpoint_markers_are_preserved(self):
        functions = set(re.findall(
            r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", self.js))
        self.assertTrue(REQUIRED_FUNCTIONS.issubset(functions),
                        f"Missing functions: {sorted(REQUIRED_FUNCTIONS - functions)}")
        for marker in REQUIRED_ENDPOINT_MARKERS:
            self.assertIn(marker, self.js)

    def test_collect_settings_keeps_the_generation_payload_contract(self):
        match = re.search(
            r"function\s+collectSettings\s*\(\)\s*\{(.*?)\n\}\s*\n\s*async\s+function\s+suggestStyle",
            self.js,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "collectSettings() block was not found")
        block = match.group(1)
        keys = set(re.findall(r"^\s*([A-Za-z_][\w]*)\s*:", block, re.MULTILINE))
        self.assertTrue(REQUIRED_SETTING_KEYS.issubset(keys),
                        f"Missing setting keys: {sorted(REQUIRED_SETTING_KEYS - keys)}")
        self.assertRegex(block, r"outro_on\s*:\s*true")
        self.assertIn("captions:", block)

    def test_phase_two_workspace_views_steps_and_inspector_are_contractual(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_TWO_IDS.issubset(ids),
                        f"Missing Phase 2 IDs: {sorted(PHASE_TWO_IDS - ids)}")
        views = set(re.findall(r'\bdata-view-panel=["\']([^"\']+)["\']', self.template))
        self.assertEqual(views, {
            "dashboard", "create", "characters", "projects", "templates",
            "assets", "settings",
        })
        nav_views = set(re.findall(
            r'class=["\'][^"\']*nav-item[^"\']*["\'][^>]*\bdata-view=["\']([^"\']+)',
            self.template,
        ))
        self.assertEqual(nav_views, views)
        self.assertEqual(
            set(re.findall(r'\bdata-step-panel=["\']([1-4])["\']', self.template)),
            {"1", "2", "3", "4"},
        )
        self.assertEqual(
            set(re.findall(r'\bdata-inspector-step=["\']([1-4])["\']', self.template)),
            {"1", "2", "3", "4"},
        )
        for function in (
            "initStudioWorkspace", "showStudioView", "setCreateStep",
            "toggleInspector", "toggleTopPopover", "saveWorkspaceDraft",
            "restoreWorkspaceDraft", "renderWorkflowSummary",
        ):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")

    def test_local_svg_sprite_is_valid_and_uses_current_color(self):
        source = ICONS.read_text(encoding="utf-8")
        root = ET.fromstring(source)
        symbols = {
            node.attrib.get("id")
            for node in root.findall("{http://www.w3.org/2000/svg}symbol")
        }
        self.assertTrue(REQUIRED_ICON_IDS.issubset(symbols))
        self.assertIn("currentColor", source)
        self.assertNotIn("<script", source.lower())
        self.assertNotIn("<image", source.lower())

    def test_flask_serves_template_and_all_phase_one_static_assets(self):
        client = app_module.app.test_client()
        page = client.get("/")
        try:
            self.assertEqual(page.status_code, 200)
            html = page.get_data(as_text=True)
            self.assertIn("/static/css/studio.css?v=20260713-phase1", html)
            self.assertIn("/static/js/studio.js?v=20260713-phase1", html)
        finally:
            page.close()
        for asset in (
            "/static/css/studio.css",
            "/static/js/studio.js",
            "/static/icons/icons.svg",
            "/static/icons/favicon.svg",
        ):
            response = client.get(asset)
            try:
                self.assertEqual(response.status_code, 200, asset)
                self.assertGreater(len(response.data), 100, asset)
            finally:
                response.close()


if __name__ == "__main__":
    unittest.main()
