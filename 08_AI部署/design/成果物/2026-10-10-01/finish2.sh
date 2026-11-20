#!/bin/bash
# 日本酒 v2 セット（2026-10-10-01 作り直し）の仕上げ：原画 sake.png を貼り直し → blend_poster3b.py（型 sake）。既にあるファイルは作り直さない
# 4隅は frame_edges_sat.py（白木の額用・あざやかさで探す）で出し、額に紙がはみ出さないよう各点を約0.7px 内側へ寄せた
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/sake.png'; B=553,97,2536,2903
declare -A F=([1]=sake-holiday2-angle1-v1 [2]=sake-holiday2-angle2-v2 [3]=sake-holiday2-angle3-v1 [4]=sake-holiday2-angle2-v1)
declare -A P=([1]="295.3,128.8 533.7,99.0 534.0,501.8 297.5,505.3" [2]="251.0,116.7 629.7,111.2 629.0,639.4 251.2,641.8" [3]="163.6,118.2 776.6,118.3 776.5,1009.8 163.2,1009.8" [4]="")
for a in 1 2 3; do
  base=${F[$a]}
  [ -f $base-orig.png ] || python ../../paste_poster.py $base.png "$O" $base-orig.png "${P[$a]}" $B
  [ -f $base-blend.png ] || python ../../blend_poster3b.py $base-orig.png $base.png $base-blend.png "${P[$a]}" 0.8 sake
done
