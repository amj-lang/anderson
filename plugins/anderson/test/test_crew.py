"""crew.py summons the lens seats from what the diff touches — run it against a real scratch repo."""
import os
import subprocess
import sys
import tempfile
import unittest

CREW = os.path.join(os.path.dirname(__file__), "..", "bin", "crew.py")


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TestCrew(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        os.makedirs(os.path.join(self.repo, "src"))
        self.write("src/list.tsx", "export const a = 1;\nexport function old() { return a; }\n")
        self.write("README.md", "hello\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    def write(self, rel, text):
        with open(os.path.join(self.repo, rel), "w") as f:
            f.write(text)

    def run_crew(self, tier, *files):
        out = subprocess.run([sys.executable, CREW, tier, *files], cwd=self.repo,
                             capture_output=True, text=True, check=True).stdout
        return {line.split()[0]: line.split()[2] for line in out.splitlines() if line != "none"}

    def test_docs_only_trivial_summons_nobody(self):
        self.write("README.md", "hello again\n")
        self.assertEqual(self.run_crew("trivial", "README.md"), {})

    def test_new_auth_file_summons_seraph_not_merovingian(self):
        os.makedirs(os.path.join(self.repo, "src/auth"))
        self.write("src/auth/login.ts", "export const login = () => 1;\n")  # untracked
        self.assertEqual(self.run_crew("normal", "src/auth/login.ts"), {"security": "reviewer"})

    def test_modified_component_with_effect_summons_niobe_and_merovingian(self):
        self.write("src/list.tsx", "export const a = 1;\nuseEffect(() => fetchAll(), [a]);\n")
        self.assertEqual(self.run_crew("normal", "src/list.tsx"),
                         {"performance": "reviewer-medium", "leftovers": "reviewer-medium"})

    def test_hard_tier_forces_seraph_and_lifts_niobe_to_high(self):
        self.write("src/list.tsx", "export const a = 1;\nexport function old() { return a; }\n"
                                   "setInterval(tick, 10);\n")
        self.assertEqual(self.run_crew("hard", "src/list.tsx"),
                         {"security": "reviewer", "performance": "reviewer"})


if __name__ == "__main__":
    unittest.main()
