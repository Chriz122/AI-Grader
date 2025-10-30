#資料輸入
print("\t\t/**這是計算出球的表面積及體積的程式**/\n")
B=float(input("\t\t請輸入球的半徑(cm):"))

import math 

#表面積與體積計算公式
S=(4/3*math.pi*B*B*B)
M=(4*math.pi*B*B)

#輸出結果
print("\n\t\t表面積: %.2f (cm²)" %S)
print("\n\t\t體積: %.2f (cm³)" %M)