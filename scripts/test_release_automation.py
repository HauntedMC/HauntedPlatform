import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("update_consumers", SCRIPTS / "update-consumers.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class ReleaseAutomationTest(unittest.TestCase):
    def test_updater_only_advances_internal_properties_and_parent(self):
        pom = ("<parent><groupId>nl.hauntedmc.platform</groupId>"
               "<artifactId>haunted-library-parent</artifactId><version>1.6.10</version></parent>"
               "<properties><haunted.dataprovider.version>3.4.3</haunted.dataprovider.version></properties>")
        updated, changed = updater.replace_parent(pom, "2.0.0")
        self.assertTrue(changed)
        updated, changed = updater.replace_property(
            updated, "haunted.dataprovider.version", "3.4.4"
        )
        self.assertTrue(changed)
        self.assertIn("<version>2.0.0</version>", updated)
        self.assertIn("<haunted.dataprovider.version>3.4.4</haunted.dataprovider.version>", updated)
        self.assertFalse(updater.replace_property(updated, "haunted.dataprovider.version", "3.4.3")[1])

    def test_reconciliation_order_contains_every_upstream_first(self):
        order = {target[0]: index for index, target in enumerate(updater.TARGETS)}
        for target, upstream, _, _ in updater.TARGETS:
            for dependency in upstream:
                self.assertLess(order[dependency], order[target])

    def test_independent_plugins_receive_platform_updates(self):
        targets = {name: (upstream, properties, module)
                   for name, upstream, properties, module in updater.TARGETS}
        for key, repository in (("dungeons", "Dungeons"),
                                ("ailex", "AIlex"),
                                ("craftgpt", "CraftGPT"),
                                ("velocityhotreloader", "VelocityHotReloader"),
                                ("paperhotreloader", "PaperHotReloader"),
                                ("webapp", "WebApp")):
            self.assertEqual(updater.PROJECTS[key], (repository, "pom.xml", "v"))
            self.assertEqual(targets[key], ((), {}, None))

        application_pom = ("<parent><groupId>nl.hauntedmc.platform</groupId>"
                           "<artifactId>haunted-application-parent</artifactId>"
                           "<version>2.0.0</version></parent>")
        updated, changed = updater.replace_parent(application_pom, "2.0.1")
        self.assertTrue(changed)
        self.assertIn("<version>2.0.1</version>", updated)

    def test_pending_upstream_blocks_downstream_pr(self):
        with patch.object(updater, "gh_json", return_value=[{
            "head": {"ref": "automation/internal-dependencies"}
        }]):
            self.assertTrue(updater.pending("dataprovider", {"dataprovider": "3.4.4"}))
        with patch.object(updater, "gh_json", return_value=[]), patch.object(
            updater, "main_pom", return_value="<revision>3.4.5</revision>"
        ):
            self.assertTrue(updater.pending("dataprovider", {"dataprovider": "3.4.4"}))
            self.assertFalse(updater.pending("dataprovider", {"dataprovider": "3.4.5"}))
        with patch.object(updater, "gh_json", return_value=[]), patch.object(
            updater, "main_pom",
            return_value="<revision>3.4.4</revision>"
                         "<haunted.theme.version>1.2.0</haunted.theme.version>"
        ):
            self.assertTrue(updater.pending(
                "dataprovider", {"dataprovider": "3.4.4", "palette": "1.2.1"}
            ))

    def test_paused_application_actions_do_not_block_dependency_prs(self):
        with patch.object(updater, "gh_json", return_value=[]), patch.object(
            updater, "main_pom", return_value="<revision>5.7.1</revision>"
        ):
            self.assertFalse(updater.pending("proxyfeatures", {"proxyfeatures": "5.3.1"}))
            self.assertFalse(updater.pending("serverfeatures", {"serverfeatures": "5.2.6"}))
            self.assertFalse(updater.pending("webapp", {"webapp": "0.0.1"}))

    def test_manual_release_pr_blocks_bot_update(self):
        pulls = [{"head": {"ref": "release/v5.7.2"}}]
        self.assertTrue(updater.manual_version_pr("proxyfeatures", pulls))
        self.assertFalse(updater.manual_version_pr("palette", pulls))
        self.assertTrue(updater.manual_version_pr(
            "palette", [{"head": {"ref": "release/palette-v1.2.3"}}]
        ))
        with patch.object(updater, "gh_json", return_value=pulls):
            self.assertTrue(updater.pending("proxyfeatures", {"proxyfeatures": "5.3.1"}))

    def test_scheduled_scan_does_not_require_release_payload(self):
        with patch.dict("os.environ", {"GITHUB_EVENT_NAME": "schedule", "RELEASE_PAYLOAD": "{}"}), \
             patch.object(updater, "published_versions", return_value={}), \
             patch.object(updater, "run"), \
             patch.object(updater, "validate_graph"), \
             patch.object(updater, "pending", return_value=True), \
             patch.object(updater, "reconcile"):
            updater.main()

    def test_graph_detects_a_missing_consumer_property(self):
        pom = ("<revision>1.2.3</revision><parent>"
               "<groupId>nl.hauntedmc.platform</groupId>"
               "<artifactId>haunted-library-parent</artifactId><version>2.0.0</version>"
               "</parent>")
        with patch.object(updater, "main_pom", return_value=pom):
            with self.assertRaisesRegex(ValueError, "haunted.theme.version"):
                updater.validate_graph()

    def test_graph_matches_local_checkout_when_all_projects_are_present(self):
        projects_root = SCRIPTS.parents[1]
        folders = {"Theme": "HauntedMCTheme"}
        required = {
            key: projects_root / folders.get(repo, repo) / pom
            for key, (repo, pom, _) in updater.PROJECTS.items()
            if key != "platform"
        }
        if not all(path.is_file() for path in required.values()):
            self.skipTest("Sibling project checkouts are unavailable")
        with patch.object(updater, "main_pom",
                          side_effect=lambda key: required[key].read_text()):
            updater.validate_graph()

    def test_existing_aligned_pr_is_not_reprepared_or_pushed(self):
        base_pom = (
            "<revision>3.4.5</revision><parent>"
            "<groupId>nl.hauntedmc.platform</groupId>"
            "<artifactId>haunted-library-parent</artifactId><version>1.6.8</version>"
            "</parent><haunted.theme.version>1.2.1</haunted.theme.version>"
        )
        remote_pom = base_pom.replace("3.4.5", "3.4.6").replace(
            "1.6.8", "2.0.0").replace("1.2.1", "1.2.2")
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(args)
            if args[:2] == ("git", "rev-parse"):
                return "base-sha\n"
            if args[:2] == ("git", "merge-base"):
                return "base-sha\n"
            if args[:2] == ("git", "show"):
                return remote_pom
            return ""

        with patch.object(updater, "main_pom", return_value=base_pom), \
             patch.object(updater, "open_pulls", return_value=[{
                 "head": {"ref": "automation/internal-dependencies"}
             }]), patch.object(updater, "run", side_effect=fake_run):
            updater.reconcile("dataprovider",
                              {"haunted.theme.version": "palette"}, None,
                              {"platform": "2.0.0", "palette": "1.2.2",
                               "dataprovider": "3.4.5"})
        self.assertNotIn(("gh", "haunted-release", "publish-pr"), calls)
        self.assertFalse(any(args and args[0] == "./tools/release/prepare-version.sh"
                             for args in calls))

    def test_paginated_github_lists(self):
        with patch.object(updater, "gh_json", side_effect=[[None] * 100, ["last"]]) as api:
            self.assertEqual(len(updater.gh_json_pages("repos/HauntedMC/Theme/releases")), 101)
        self.assertIn("page=2", api.call_args_list[-1].args[0])


if __name__ == "__main__":
    unittest.main()
