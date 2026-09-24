import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("update_consumers", SCRIPTS / "update-consumers.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class ReleaseAutomationTest(unittest.TestCase):
    def test_gate_publishes_only_new_untagged_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            pom = root / "pom.xml"
            pom.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0">'
                           '<properties><revision>1.2.3</revision></properties></project>')
            subprocess.run(["git", "add", "pom.xml"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "old"], cwd=root, check=True)
            before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            pom.write_text(pom.read_text().replace("1.2.3", "1.2.4"))
            env = dict(os.environ, GITHUB_EVENT_BEFORE=before, GITHUB_EVENT_NAME="push")
            result = subprocess.check_output(
                ["python3", str(SCRIPTS / "release-gate.py"), "--tag-prefix", "palette-"],
                cwd=root, env=env, text=True,
            )
            self.assertIn("publish: True", result)
            self.assertIn("palette-v1.2.4", result)
            same_version = subprocess.check_output(
                ["python3", str(SCRIPTS / "release-gate.py"), "--tag-prefix", "palette-"],
                cwd=root, env=dict(env, GITHUB_EVENT_BEFORE=""), text=True,
            )
            self.assertIn("publish: True", same_version)
            subprocess.run(["git", "add", "pom.xml"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "new"], cwd=root, check=True)
            subprocess.run(["git", "tag", "palette-v1.2.4"], cwd=root, check=True)
            result = subprocess.check_output(
                ["python3", str(SCRIPTS / "release-gate.py"), "--tag-prefix", "palette-"],
                cwd=root, env=env, text=True,
            )
            self.assertIn("publish: False", result)

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


if __name__ == "__main__":
    unittest.main()
