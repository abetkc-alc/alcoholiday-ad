#!/bin/bash
# 8畳版（v2）の仕上げ：原画を貼り直し → blend_poster2.py。使い方: finish8.sh [接尾辞（標準 blend）] [色味の強さ]
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/whisky.jpg'; B=500,78,2518,2934
declare -A P=([1]="378,189.5 578.5,189.5 578,475.5 378,476" [2]="331.5,190.5 610,190.5 610,570 332,570" [3]="144,235.5 788,236.5 788,1130.5 144,1130.5")
S=${1:-blend}; T=${2:-0.4}
for a in 1 2 3; do
  base=whisky-soccer8-angle$a-v2
  [ -f $base-orig.png ] || python ../../paste_poster.py $base.png "$O" $base-orig.png "${P[$a]}" $B
  [ -f $base-$S.png ] && { echo "SKIP $base-$S.png"; continue; }
  python ../../blend_poster2.py $base-orig.png $base.png $base-$S.png "${P[$a]}" $T
done
