# Claude から Codex（OpenAI）に仕事をたのむ入口（2026-10-16）
#   ・Codex の置き場所（AppData/Local/OpenAI/Codex/bin/<英数字>/codex.exe）は更新で変わるので、毎回いちばん新しいものを探す
#   ・指示文は標準入力で渡す（-i は画像をいくつでも受け取るので、後ろに書いた指示文まで画像の名前だと思われて止まるため）
#   ・Codex の最後の返事を画面に出し、--out を指定すればファイルにも残す
#
# 使い方:
#   python 08_AI部署/data/codex.py "指示文" [-C 作業フォルダ] [-i 画像 ...] [--readonly] [--out 返事.md] [--timeout 秒]
#   python 08_AI部署/data/codex.py --prompt-file 指示.md -C 08_AI部署/design/成果物/2026-10-16-01 -i ポスター.jpg
#   --readonly：ファイルを書きかえさせない（見直し・相談だけのとき）。つけなければ作業フォルダの中だけ書きかえてよい
#   --where：見つけた Codex の場所と版だけを出す
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

BIN = pathlib.Path(os.environ.get("LOCALAPPDATA", r"C:\Users\abetk\AppData\Local")) / "OpenAI" / "Codex" / "bin"


def find_codex():
    """いちばん新しい codex.exe（rg.exe だけのフォルダもあるので、codex.exe があるフォルダだけ見る）"""
    found = sorted(BIN.glob("*/codex.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
    if found:
        return found[0]
    p = shutil.which("codex")
    if p:
        return pathlib.Path(p)
    raise SystemExit(f"Codex が見つかりません（{BIN} に codex.exe がない）。Codex のアプリを一度ひらくと入ります")


def main():
    ap = argparse.ArgumentParser(description="Claude から Codex に仕事をたのむ")
    ap.add_argument("prompt", nargs="?", help="Codex への指示文")
    ap.add_argument("--prompt-file", help="指示文を書いたファイル（長い指示のとき）")
    ap.add_argument("-C", "--cd", default=".", help="Codex が作業するフォルダ（ここより外は書きかえさせない）")
    ap.add_argument("-i", "--image", action="append", default=[], help="Codex に見せる画像（何枚でも。-i を画像ごとにつける）")
    ap.add_argument("--readonly", action="store_true", help="ファイルを書きかえさせない")
    ap.add_argument("--out", help="Codex の最後の返事を保存するファイル")
    ap.add_argument("--timeout", type=int, default=1800, help="この秒数をすぎたら止める（はじめは30分）")
    ap.add_argument("--where", action="store_true", help="Codex の場所と版だけ出す")
    a = ap.parse_args()

    codex = find_codex()
    if a.where:
        ver = subprocess.run([str(codex), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
        print(f"{codex}\n{ver}")
        return
    if a.prompt_file:
        prompt = pathlib.Path(a.prompt_file).read_text(encoding="utf-8")
    elif a.prompt:
        prompt = a.prompt
    else:
        raise SystemExit("指示文がありません（\"指示文\" か --prompt-file）")
    cd = pathlib.Path(a.cd).resolve()
    if not cd.is_dir():
        raise SystemExit(f"作業フォルダがありません: {cd}")
    for im in a.image:
        if not pathlib.Path(im).exists():
            raise SystemExit(f"画像が見つかりません: {im}")

    if a.out:
        last = pathlib.Path(a.out).resolve()
    else:
        fd, tmp = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        last = pathlib.Path(tmp)
    cmd = [str(codex), "exec", "--skip-git-repo-check", "-C", str(cd),
           "-s", "read-only" if a.readonly else "workspace-write", "-o", str(last)]
    for im in a.image:
        cmd += ["-i", str(pathlib.Path(im).resolve())]
    print(f"Codex：{codex.parent.name}／作業フォルダ：{cd}／{'読むだけ' if a.readonly else '書きかえ可'}", flush=True)
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=a.timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"Codex が {a.timeout} 秒たっても終わりませんでした（止めました）")
    reply = last.read_text(encoding="utf-8", errors="replace").strip() if last.exists() else ""
    if r.returncode != 0 or not reply:
        sys.stderr.write((r.stderr or r.stdout)[-3000:])
        raise SystemExit(f"Codex が失敗しました（終了コード {r.returncode}）")
    print("----- Codex の返事 -----")
    print(reply)
    if not a.out:
        last.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
