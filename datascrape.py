from pathlib import Path

import db
import utilitys


def run():
    print("Check/Train/Clean")
    folder = Path(__file__).parent / "content"
    for txt_path in folder.glob("*.txt"):
        content = txt_path.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        for idx in range(len(lines) - 1):
            first = utilitys.clean_message(lines[idx])
            second = utilitys.clean_message(lines[idx + 1])
            for token in first.split():
                db.add_menu_item(token)
                db.add_ingredient_or_increment(token, second)
        try:
            txt_path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"Could not delete {txt_path}: file is in use")


if __name__ == "__main__":
    db.init_db()
    run()
