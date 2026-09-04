#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""標準入力を読み、個人が特定できそうな文字を伏せてから標準出力に流す。

【なぜあるか】
  このリポジトリは**公開**なので、GitHub Actions の実行ログを誰でも読める。
  実行するスクリプト自体は非公開リポジトリから取り出して動かすが、
  スクリプトが print した文字はそのまま公開ログに載ってしまう。
  「いまはログに患者名が出ていない」ことは直近5回ぶんのログで確認済みだが、
  **将来うっかり患者名を出すコードが入る**可能性を仕組みで潰すため、
  すべての出力をこのフィルタに通す。

【使い方】ワークフロー側で
    set -o pipefail
    python -u なにか.py 2>&1 | python ../mask.py
  pipefail を付けないと、スクリプトが失敗してもジョブが成功扱いになるので必ず付ける。

【伏せるもの】カルテ番号とそのうしろに続く氏名／○○様・○○さん／電話番号／
  メールアドレス／生年月日／patient_id の値。
【伏せないもの】件数・日付・処理の段階・エラーの種類（＝原因を追うのに要るもの）。
"""
import re
import sys

# 医院として公開している連絡先や、GitHub が自分で出す文字は伏せない（読めないと不便なだけ）
KEEP = re.compile(r"03-5739-1625|github|noreply|actions@|ovalcourtdental|worksmobile|googleapis")

# 「カルテ番号 → 氏名」の並びが医院の書式なので、番号のうしろに続く氏名ごと伏せる
_NAME = r"(?:[一-龥ぁ-ゖァ-ー]{1,6}[ 　]{0,2}){1,3}"

RULES = [
    (re.compile(r"No\.\s*\d{2,}\s*" + _NAME), "No.●●●● ●●●"),
    (re.compile(r"(No\.\s*)\d{2,}"), r"\1●●●●"),
    (re.compile(r"patient[_ ]?id[\"']?\s*[:=]\s*[\"']?\d+", re.I), "patient_id=●●●●"),
    (re.compile(_NAME + r"(様|さん|氏)(?![式々])"), r"●●●\1"),
    (re.compile(r"0\d{1,4}-\d{2,4}-\d{3,4}"), "●●-●●●●-●●●●"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"), "●●●@●●●"),
    (re.compile(r"(19|20)\d{2}[/-]\d{1,2}[/-]\d{1,2}\s*(生|生まれ)"), "●●●●年●月●日生"),
]

# KEEP に当たる行でも、この番号までは必ず伏せる（氏名・カルテ番号・patient_id）
ALWAYS = 4


def mask(line: str) -> str:
    rules = RULES[:ALWAYS] if KEEP.search(line) else RULES
    for rx, rep in rules:
        line = rx.sub(rep, line)
    return line


def main() -> None:
    for line in sys.stdin:
        sys.stdout.write(mask(line))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
