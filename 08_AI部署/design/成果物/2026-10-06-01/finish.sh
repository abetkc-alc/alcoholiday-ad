#!/bin/bash
# 仕上げ（原画の貼り直し＋なじませ）。v3 が納品版。額の内側の四隅（左上 右上 右下 左下）
O='C:/Users/abetk/Desktop/ALCOHOLIDAY/画像/商品画像/ORIGINAL/whisky.jpg'; B=500,78,2518,2934
declare -A P=([1]="242.5,150.5 458.5,169.5 458.5,504 245,513" [2]="260,135.5 559,155 559,582 259.5,583.5" [3]="150,166.5 821,174 821,1108.5 149.5,1108.5")
V=${1:-v4}
for a in 1 2 3; do
  [ -f whisky-soccer-angle$a-v1-blend-$V.png ] && { echo "SKIP $V"; continue; }
  python ../../paste_poster.py whisky-soccer-angle$a-v1.png "$O" whisky-soccer-angle$a-v1-orig-$V.png "${P[$a]}" $B
  python ../../blend_poster.py whisky-soccer-angle$a-v1-orig-$V.png whisky-soccer-angle$a-v1-blend-$V.png "${P[$a]}"
done
