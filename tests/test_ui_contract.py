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
    "/api/cost", "/api/export/", "/api/project/", "/open-folder", "/projects/",
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
    "icon-arrow-up", "icon-arrow-down", "icon-warning", "icon-clock",
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

PHASE_THREE_IDS = {
    "scriptModeTabs", "scriptWritePanel", "scriptAIPanel",
    "scriptLanguageIndicator", "generationToast", "generationToastMessage",
    "undoGeneratedScriptBtn", "keepGeneratedScriptBtn",
}

PHASE_FOUR_IDS = {
    "previewPlanStatus", "pvCharacterCount", "pvSceneCount",
    "pvDialogueCount", "previewValidation", "castSectionTitle",
    "scenesSectionTitle", "castContinueBtn", "castInspectorSelection",
    "castInspectorScene", "castInspectorDuration", "castInspectorMood",
}

PHASE_FIVE_IDS = {
    "advancedSettingsBackdrop", "advancedSettingsDrawer",
    "advancedSettingsTitle", "advancedSettingsClose", "advancedRenderGroup",
    "advancedCaptionsGroup", "advancedProviderGroup",
    "advancedProviderDetails", "musicVolumeValue",
}

PHASE_SIX_IDS = {
    "renderReadyExperience", "renderPreviewSurface", "renderProjectTitle",
    "renderEstimatedDuration", "renderEstimatedCost", "renderFormatSummary",
    "renderVoiceSummary", "renderCaptionSummary", "generationStage",
    "generationClip", "generationResumeStatus", "overallProgress",
    "overallProgressFill", "overallProgressLabel", "generationElapsed",
    "openProjectFolderBtn", "exportOptionsButton", "exportOptionsPanel",
    "exportSrt", "exportAudio", "exportThumbnail", "exportSeo", "exportBtn",
    "exportResult",
}

PHASE_SEVEN_IDS = {
    "dashboardProviderHealth", "dashboardEngineDetail",
    "dashboardCompletedCount", "dashboardUnfinishedCount",
    "dashboardSceneCount", "dashboardRecentProjects", "projectListToggle",
    "deleteProjectDialog", "deleteProjectDialogTitle",
    "deleteProjectDialogMessage", "confirmProjectDeleteButton",
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
        self.assertIn("?v=20260714-phase7", self.template)
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

    def test_phase_three_script_modes_and_ai_generators_are_contractual(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_THREE_IDS.issubset(ids),
                        f"Missing Phase 3 IDs: {sorted(PHASE_THREE_IDS - ids)}")
        self.assertEqual(
            re.findall(r'\bdata-script-mode=["\']([^"\']+)["\']', self.template),
            ["write", "ai"],
        )
        self.assertEqual(
            set(re.findall(r'<button[^>]+\bdata-t=["\']([^"\']+)', self.template)),
            {"quick", "longform", "series", "templates"},
        )
        self.assertEqual(
            set(re.findall(r'<div[^>]+class=["\'][^"\']*tabpanel[^"\']*["\'][^>]+\bdata-t=["\']([^"\']+)', self.template)),
            {"quick", "longform", "series", "templates"},
        )
        for function in (
            "selectScriptMode", "selectAIGenerator", "openAIGenerator",
            "replaceScriptWithGenerated", "showGenerationToast",
            "undoGeneratedScript", "acceptGeneratedScript",
            "updateScriptLanguageIndicator",
        ):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")
        self.assertIn("scriptMode:STUDIO_UI.scriptMode", self.js)
        self.assertIn("aiTab:STUDIO_UI.aiTab", self.js)

    def test_phase_four_cast_scene_editor_preserves_edited_plan_contract(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_FOUR_IDS.issubset(ids),
                        f"Missing Phase 4 IDs: {sorted(PHASE_FOUR_IDS - ids)}")
        for function in (
            "previewDuration", "speakerOptions", "updateSceneOrderLabels",
            "moveSceneCard", "validatePreviewPlan", "continueFromCast",
            "selectPreviewScene", "selectPreviewLine",
        ):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")
        for selector in (
            "character-card", "scene-card", "dialogue-row", "pvSpeaker",
            "pvEmo", "pvAction", "pvText", "pvBg", "pvMood",
        ):
            self.assertIn(selector, self.js + self.css)
        collect = re.search(
            r"function\s+collectEditedParsed\s*\(\)\s*\{(.*?)\n\}",
            self.js,
            re.DOTALL,
        )
        self.assertIsNotNone(collect)
        block = collect.group(1)
        for field in ("speaker", "emotion", "action", "text", "background_prompt", "mood"):
            self.assertIn(field, block)
        self.assertIn("p.scenes=reorderedScenes", block)

    def test_phase_five_uses_progressive_disclosure_without_losing_settings(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_FIVE_IDS.issubset(ids),
                        f"Missing Phase 5 IDs: {sorted(PHASE_FIVE_IDS - ids)}")
        drawer = re.search(
            r'id=["\']advancedSettingsDrawer["\'](.*?)</aside>',
            self.template,
            re.DOTALL,
        )
        self.assertIsNotNone(drawer)
        advanced_markup = drawer.group(1)
        for setting_id in (
            "render_engine", "fps", "gpu_encode", "fast_preview",
            "motionSeg", "modeSeg", "multiChar", "vignette", "intro_on",
            "cap_words", "cap_size", "posSeg", "cap_hl", "hlSeg",
            "cap_perspk", "test_img", "testBtn", "testResult",
        ):
            self.assertRegex(advanced_markup, rf'\bid=["\']{setting_id}["\']')
        for function in ("toggleAdvancedSettings", "syncAdvancedSettingsUI"):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")
        self.assertIn("#studioShell,#advancedSettingsDrawer", self.js)
        self.assertIn("advanced-settings-open", self.css)
        self.assertGreaterEqual(self.template.count("data-advanced-settings-trigger"), 4)

    def test_phase_six_render_experience_keeps_generation_and_export_flows(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_SIX_IDS.issubset(ids),
                        f"Missing Phase 6 IDs: {sorted(PHASE_SIX_IDS - ids)}")
        for function in (
            "getRenderMetrics", "formatRenderDuration", "updateRenderEstimate",
            "setGenerationExperience", "startGenerationClock",
            "stopGenerationClock", "generatePreferred", "openProjectFolder",
            "toggleExportOptions", "exportProject", "createAnotherVideo",
        ):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")
        self.assertIn("/api/cost", self.js)
        self.assertIn("/api/export/", self.js)
        self.assertIn("/open-folder", self.js)
        self.assertIn("aspect-ratio:16/9", self.css)
        self.assertIn("role=\"progressbar\"", self.template)

    def test_phase_seven_dashboard_projects_and_delete_dialog_are_contractual(self):
        ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', self.template))
        self.assertTrue(PHASE_SEVEN_IDS.issubset(ids),
                        f"Missing Phase 7 IDs: {sorted(PHASE_SEVEN_IDS - ids)}")
        for function in (
            "formatProjectDuration", "formatProjectDate", "projectCardMarkup",
            "recentProjectMarkup", "closeProjectMenus", "toggleProjectMenu",
            "handleProjectAction", "requestProjectDelete",
            "closeDeleteProjectDialog", "confirmProjectDelete",
        ):
            self.assertRegex(self.js, rf"function\s+{function}\s*\(")
        for selector in (
            "dashboard-hero-grid", "dashboard-stats", "project-card-grid",
            "project-thumbnail", "project-menu", "confirm-dialog",
        ):
            self.assertIn(selector, self.template + self.css + self.js)
        self.assertNotIn("if(!confirm('", self.js)

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
            self.assertIn("/static/css/studio.css?v=20260714-phase7", html)
            self.assertIn("/static/js/studio.js?v=20260714-phase7", html)
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
