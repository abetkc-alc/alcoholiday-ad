#!/bin/bash
# 日本酒 v4 セット（2026-10-10-01 作り直し3回目）の仕上げ：原画 sake.png を貼り直し → blend_poster3b.py（型 sake）。既にあるファイルは作り直さない
# 4隅は frame_edges_sat.py で出し（3枚とも額は長方形・ずれ±0.6px以内）、額に紙がはみ出さないよう各点を約0.7px 内側へ寄せた
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/sake.png'; B=553,97,2536,2903
declare -A F=([1]=sake-holiday4-angle1-v7 [2]=sake-holiday4-angle2-v2 [3]=sake-holiday4-angle3-v1)
declare -A P=([1]="226.1,98.2 545.7,97.8 546.0,546.7 225.8,546.8" [2]="150.0,103.4 623.5,103.2 623.2,769.4 150.0,769.5" [3]="164.6,168.4 783.9,168.4 783.4,1039.7 164.7,1039.7")
for a in 1 2 3; do
  base=${F[$a]}
  [ -f $base-orig.png ] || python ../../paste_poster.py $base.png "$O" $base-orig.png "${P[$a]}" $B
  [ -f $base-blend.png ] || python ../../blend_poster3b.py $base-orig.png $base.png $base-blend.png "${P[$a]}" 0.8 sake
done
