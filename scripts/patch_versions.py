"""绕过 transformers 4.51 的依赖版本检查（仅用于测试 CosyVoice2）。"""
import sys

# 在 import transformers 前 patch require_version
import transformers.utils.versions as tv


def _require_version(requirement, hint=None):
    pass


def _require_version_core(requirement, hint=None):
    pass


def _require_version_greater_equal(requirement, hint=None):
    pass


tv.require_version = _require_version
tv.require_version_core = _require_version_core
tv.require_version_greater_equal = _require_version_greater_equal

import transformers  # noqa: E402

print("transformers:", transformers.__version__)
