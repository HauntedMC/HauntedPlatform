import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "optional_maven", SCRIPTS / "make-local-maven-optional.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class OptionalLocalMavenTest(unittest.TestCase):
    def setUp(self):
        self.protection = {
            "strict": True,
            "contexts": ["ci-required", "hauntedmc/local-maven"],
            "checks": [
                {"context": "hauntedmc/local-maven", "app_id": -1},
                {"context": "security-scan", "app_id": 123},
            ],
        }

    def test_filters_only_local_check_preserving_other_protections(self):
        changed, result = helper.without_local_check(self.protection)
        self.assertTrue(changed)
        self.assertEqual(result, {
            "strict": True,
            "contexts": ["ci-required"],
            "checks": [{"context": "security-scan", "app_id": 123}],
        })
        self.assertEqual(len(self.protection["checks"]), 2)

    def test_no_change_for_nonrequired_local_check(self):
        changed, result = helper.without_local_check({
            "strict": False, "contexts": ["ci-required"], "checks": [],
        })
        self.assertFalse(changed)
        self.assertFalse(result["strict"])

    def test_preview_never_patches_branch_protection(self):
        with patch.object(helper, "required_statuses", return_value=self.protection), \
             patch.object(helper, "inspect_rulesets"), \
             patch.object(helper, "gh") as api:
            self.assertEqual(helper.run(["ProxyFeatures"], apply=False), 0)
            api.assert_not_called()

    def test_apply_patches_and_verifies(self):
        after = {"strict": True, "contexts": ["ci-required"],
                 "checks": [{"context": "security-scan", "app_id": 123}]}
        with patch.object(helper, "required_statuses", side_effect=[self.protection, after]), \
             patch.object(helper, "inspect_rulesets"), \
             patch.object(helper, "gh") as api:
            self.assertEqual(helper.run(["WebApp"], apply=True), 0)
            api.assert_called_once_with(
                "repos/HauntedMC/WebApp/branches/main/protection/required_status_checks",
                method="PATCH", payload=after,
            )

    def test_failed_post_update_confirmation_is_not_silent(self):
        with patch.object(helper, "required_statuses",
                          side_effect=[self.protection, self.protection]), \
             patch.object(helper, "inspect_rulesets"), \
             patch.object(helper, "gh"):
            self.assertEqual(helper.run(["ServerFeatures"], apply=True), 1)


if __name__ == "__main__":
    unittest.main()
