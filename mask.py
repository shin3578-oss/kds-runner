#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""標準入力を読み、人の名前や連絡先を伏せてから標準出力へ流す。

【なぜあるか】
  このリポジトリは**公開**なので、GitHub Actions の実行ログを誰でも読める。
  実行するスクリプト自体は非公開リポジトリから取り出して動かすが、
  スクリプトが print した文字はそのまま公開ログに載る。
  2026-09-04の初回検証で、シフト取得のログに**スタッフの実名**がそのまま出た
  （`[Shift] API取得: ['○○', '○○', ...]`）。そのログは即削除し、この仕組みを作った。

【使い方】ワークフロー側で
    env:
      MASK_NAMES: ${{ secrets.MASK_NAMES }}
    run: |
      set -o pipefail
      python -u なにか.py 2>&1 | python ../runner/mask.py
  pipefail を付けないと、スクリプトが失敗してもジョブが成功扱いになるので必ず付ける。

【伏せかた】3段構え
  1. MASK_NAMES（Secret）に入れた実名を、出てきた形のまま全部伏せる。
     名字だけ・下の名前だけ・表記ゆれも列挙しておくこと。
  2. カルテ番号／○○様・○○さん／電話／メール／生年月日／patient_id を形で伏せる。
  3. 引用符でくくられた日本語（リスト出力に名前が並ぶ形）を伏せる。
  ★MASK_NAMES が空のときは**漢字2文字以上を全部伏せる**（設定漏れで漏らすくらいなら
    読みにくいログのほうがマシ＝安全側に倒す）。

【伏せないもの】件数・日付・処理の段階・英数字のエラーメッセージ（原因を追うのに要る）。
"""
import os
import re
import sys

# 医院として公開している連絡先や、GitHub が自分で出す文字は伏せない（読めないと不便なだけ）
KEEP = re.compile(r"03-5739-1625|github|noreply|actions@|ovalcourtdental|worksmobile|googleapis")

_JP = r"[一-龥ぁ-ゖァ-ヶー]"
_NAME = r"(?:" + _JP + r"{1,6}[ 　]{0,2}){1,3}"

RULES = [
    # 医院の書式が「カルテ番号 → 氏名」なので、番号のうしろに続く氏名ごと伏せる
    (re.compile(r"No\.\s*\d{2,}\s*" + _NAME), "No.●●●● ●●●"),
    (re.compile(r"(No\.\s*)\d{2,}"), r"\1●●●●"),
    (re.compile(r"patient[_ ]?id[\"']?\s*[:=]\s*[\"']?\d+", re.I), "patient_id=●●●●"),
    (re.compile(_NAME + r"(様|さん|氏|先生)(?![式々])"), r"●●●\1"),
    (re.compile(r"0\d{1,4}-\d{2,4}-\d{3,4}"), "●●-●●●●-●●●●"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"), "●●●@●●●"),
    (re.compile(r"(19|20)\d{2}[/-]\d{1,2}[/-]\d{1,2}\s*(生|生まれ)"), "●●●●年●月●日生"),
    # リスト出力に名前が並ぶ形（'○○', "○○"）はまとめて伏せる
    (re.compile(r"'(" + _JP + r"{2,6})'"), "'●●'"),
    (re.compile(r"\"(" + _JP + r"{2,6})\""), '"●●"'),
    (re.compile(r"（(" + _JP + r"{2,4})）"), "（●●）"),
]

# KEEP に当たる行でも、この番号までは必ず伏せる（氏名・カルテ番号・patient_id）
ALWAYS = 4


def _build_names():
    raw = os.environ.get("MASK_NAMES", "")
    names = sorted({n.strip() for n in re.split(r"[,\n]", raw) if n.strip()},
                   key=len, reverse=True)
    if names:
        return re.compile("|".join(re.escape(n) for n in names)), False
    # 設定漏れ。読みにくくても漏らさないほうを取る＝漢字2文字以上を全部伏せる
    return re.compile(r"[一-龥]+"), True


NAMES_RX, FALLBACK = _build_names()


def mask(line: str) -> str:
    line = NAMES_RX.sub("●●", line)
    for rx, rep in (RULES[:ALWAYS] if KEEP.search(line) else RULES):
        line = rx.sub(rep, line)
    return line


def main() -> None:
    if FALLBACK:
        sys.stdout.write("[mask] MASK_NAMES が空です。安全側に倒して漢字を全部伏せます。\n")
    for line in sys.stdin:
        sys.stdout.write(mask(line))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
