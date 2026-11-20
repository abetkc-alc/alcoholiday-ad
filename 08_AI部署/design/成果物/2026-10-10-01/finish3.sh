#!/bin/bash
# 日本酒 v3 セット（2026-10-10-01 作り直し2回目）の仕上げ：原画 sake.png を貼り直し → blend_poster3b.py（型 sake）。既にあるファイルは作り直さない
# 4隅は frame_edges_sat.py で出し（3枚とも額は長方形・ずれ±0.2px以内）、額に紙がはみ出さないよう各点を約0.7px 内側へ寄せた
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/sake.png'; B=553,97,2536,2903
# 最初は angle1-v2／angle2-v3／angle3-v1 で仕上げた（その -orig・-blend も残してある）。サイドボードが斜めにゆがんでいたので直した版（angle1-v3／angle2-v4／angle3-v2）を納品用にした
declare -A F=([1]=sake-holiday3-angle1-v3 [2]=sake-holiday3-angle2-v4 [3]=sake-holiday3-angle3-v2 [4]=sake-holiday3-angle1-v2 [5]=sake-holiday3-angle2-v3 [6]=sake-holiday3-angle3-v1)
declare -A P=([1]="304.6,119.5 556.5,119.1 556.5,486.9 304.4,486.9" [2]="301.7,95.5 573.9,94.9 573.9,493.0 301.6,493.1" [3]="234.1,138.7 709.7,138.9 709.6,810.9 233.4,810.7" [4]="304.4,119.8 556.5,119.0 556.6,486.7 304.3,486.8" [5]="302.0,95.4 573.7,94.9 573.8,493.1 301.6,493.1" [6]="233.9,138.6 709.7,139.0 709.7,810.8 233.5,810.8")
for a in 1 2 3 4 5 6; do
  base=${F[$a]}
  [ -f $base-orig.png ] || python ../../paste_poster.py $base.png "$O" $base-orig.png "${P[$a]}" $B
  [ -f $base-blend.png ] || python ../../blend_poster3b.py $base-orig.png $base.png $base-blend.png "${P[$a]}" 0.8 sake
done
