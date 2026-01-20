import os
import json
from threading import Lock

CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "runtime_flags.json",
)

_lock = Lock()


def _get_default_flags() -> dict:
    """
    フラグのデフォルト値を返す。
    - enable_ai_image: True なら AI 画像生成を行う
    - enable_ai_suggest: True なら AI 提案を行う
    """
    return {
        "enable_ai_image": True,
        "enable_ai_suggest": True,
    }


def load_runtime_flags() -> dict:
    """
    ランタイムのフラグを取得する。
    - JSON が存在しない場合: デフォルト値を返す
    - JSON が壊れている場合: デフォルト値を返す
    """
    defaults = _get_default_flags()

    if not os.path.exists(CONFIG_FILE_PATH):
        return defaults

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return defaults

    # 欠けているキーはデフォルトで補完し、bool 変換する
    result = defaults.copy()
    for key in ("enable_ai_image", "enable_ai_suggest"):
        if key in data:
            result[key] = bool(data[key])

    # 旧キー（use_test_image/use_test_data）が残っている場合の後方互換
    # 旧キーがあって新キーが無い場合のみ読み替える
    if "enable_ai_image" not in data and "use_test_image" in data:
        result["enable_ai_image"] = not bool(data["use_test_image"])
    if "enable_ai_suggest" not in data and "use_test_data" in data:
        result["enable_ai_suggest"] = not bool(data["use_test_data"])

    return result


def save_runtime_flags(flags: dict) -> dict:
    """
    ランタイムのフラグを更新して保存する。
    - 受け取った dict から必要なキーのみを保存
    - 返り値は保存後の最新値
    """
    with _lock:
        current = load_runtime_flags()
        if "enable_ai_image" in flags:
            current["enable_ai_image"] = bool(flags["enable_ai_image"])
        if "enable_ai_suggest" in flags:
            current["enable_ai_suggest"] = bool(flags["enable_ai_suggest"])

        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)

        return current


def get_enable_ai_image() -> bool:
    """
    AI 画像生成を行うかどうか。
    True: AI画像生成
    False: テスト画像を使用
    """
    return load_runtime_flags().get("enable_ai_image", True)


def get_enable_ai_suggest() -> bool:
    """
    AI 提案を行うかどうか。
    True: AI提案
    False: テストデータを使用
    """
    return load_runtime_flags().get("enable_ai_suggest", True)

