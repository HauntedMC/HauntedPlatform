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
             patch.object(updater, "pending", return_value=True), \
             patch.object(updater, "reconcile"):
            updater.main()


if __name__ == "__main__":
    unittest.main()
