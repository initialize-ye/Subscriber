"""Tests for deploy.yml — verify workflow structure and completeness."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_FILE = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"


@pytest.fixture
def deploy_config():
    """Load deploy.yml as a dict."""
    with open(DEPLOY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestDeployStructure:
    """Verify deploy.yml basic structure."""

    def test_file_exists(self):
        assert DEPLOY_FILE.exists(), "deploy.yml not found"

    def test_yaml_valid(self, deploy_config):
        assert isinstance(deploy_config, dict)
        assert "jobs" in deploy_config

    def test_triggers_on_push_main(self, deploy_config):
        # YAML parses 'on' as True (boolean keyword)
        triggers = deploy_config.get(True, {})
        assert "push" in triggers
        assert "main" in triggers["push"].get("branches", [])

    def test_triggers_on_workflow_dispatch(self, deploy_config):
        triggers = deploy_config.get(True, {})
        assert "workflow_dispatch" in triggers

    def test_deploy_job_exists(self, deploy_config):
        jobs = deploy_config.get("jobs", {})
        assert "deploy" in jobs

    def test_runs_on_ubuntu(self, deploy_config):
        deploy = deploy_config["jobs"]["deploy"]
        assert deploy.get("runs-on") == "ubuntu-latest"

    def test_has_timeout(self, deploy_config):
        deploy = deploy_config["jobs"]["deploy"]
        assert deploy.get("timeout-minutes") == 10

    def test_uses_ssh_action(self, deploy_config):
        steps = deploy_config["jobs"]["deploy"]["steps"]
        ssh_step = next(s for s in steps if s.get("name") == "Deploy to server")
        assert "appleboy/ssh-action" in ssh_step["uses"]

    def test_ssh_uses_secrets(self, deploy_config):
        steps = deploy_config["jobs"]["deploy"]["steps"]
        ssh_step = next(s for s in steps if s.get("name") == "Deploy to server")
        with_block = ssh_step["with"]
        assert "${{ secrets.SSH_HOST }}" in with_block["host"]
        assert "${{ secrets.SSH_USER }}" in with_block["username"]
        assert "${{ secrets.SSH_KEY }}" in with_block["key"]


class TestDeploySteps:
    """Verify the 12-step deployment pipeline exists in the SSH script."""

    @pytest.fixture
    def script(self, deploy_config):
        steps = deploy_config["jobs"]["deploy"]["steps"]
        ssh_step = next(s for s in steps if s.get("name") == "Deploy to server")
        return ssh_step["with"]["script"]

    def test_has_12_steps(self, script):
        for i in range(1, 13):
            assert f"[{i}/12]" in script, f"Missing step [{i}/12]"

    def test_step1_enter_project_dir(self, script):
        assert "进入项目目录" in script

    def test_step2_backup(self, script):
        assert "备份当前版本" in script

    def test_step3_pull_code(self, script):
        assert "拉取最新代码" in script

    def test_step4_show_changes(self, script):
        assert "代码变更" in script

    def test_step5_update_deps(self, script):
        assert "更新依赖" in script

    def test_step6_patch_bison(self, script):
        assert "patch_bison.py" in script

    def test_step7_run_tests(self, script):
        assert "运行测试" in script
        assert "pytest" in script

    def test_step8_check_playwright(self, script):
        assert "Playwright" in script

    def test_step9_syntax_check(self, script):
        assert "语法检查" in script
        assert "py_compile" in script

    def test_step10_check_config(self, script):
        assert "检查配置" in script

    def test_step11_restart_service(self, script):
        assert "重启服务" in script

    def test_step12_health_check(self, script):
        assert "健康检查" in script

    def test_rollback_on_test_failure(self, script):
        assert "测试失败，回滚部署" in script
        assert 'git reset --hard "$CURRENT_COMMIT"' in script

    def test_rollback_on_syntax_failure(self, script):
        assert "语法检查失败，回滚部署" in script

    def test_rollback_on_service_failure(self, script):
        assert "服务启动失败，回滚部署" in script

    def test_runtime_data_backup(self, script):
        assert "RUNTIME_FILES" in script
        assert ".env" in script

    def test_runtime_data_restore(self, script):
        assert "restore_runtime" in script

    def test_backup_data_dir(self, script):
        assert 'cp -rp "data"' in script

    def test_systemd_service_created(self, script):
        assert 'SERVICE_NAME="subscriber"' in script

    def test_has_status_check_step(self, deploy_config):
        steps = deploy_config["jobs"]["deploy"]["steps"]
        status_step = steps[-1]
        assert status_step.get("name") == "Deployment status"
        assert status_step.get("if") == "always()"
