#!/bin/bash
# 日本酒（2026-10-10-01）の仕上げ：原画 sake.png を貼り直し → blend_poster3b.py（型 sake）。既にあるファイルは作り直さない
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/sake.png'; B=553,97,2536,2903
declare -A F=([1]=sake-holiday-angle1-v1 [2]=sake-holiday-angle2-v2 [3]=sake-holiday-angle3-v3)
declare -A P=([1]="296.1,129.4 534.2,99.5 535.5,502.2 298.5,506.1" [2]="230,95.5 712.5,101 712.5,793.5 229,791.5" [3]="112.5,117.5 823.5,117.5 828,1134.5 112,1134.5")
for a in 1 2 3; do
  base=${F[$a]}
  [ -f $base-orig.png ] || python ../../paste_poster.py $base.png "$O" $base-orig.png "${P[$a]}" $B
  [ -f $base-blend.png ] || python ../../blend_poster3b.py $base-orig.png $base.png $base-blend.png "${P[$a]}" 0.8 sake
done
