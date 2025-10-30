#由鍵盤輸入橢圓體的赤道半徑a、b及極半徑c
# a,b,c=map(int, input(‘請輸入橢圓體的赤道半徑a、b及極半徑c:’).split(‘,’)) #每筆資料以split()指定的符號來間隔
print('請輸入橢圓體的赤道半徑a、b及極半徑c(cm)')
a=int(input('a='))
b=int(input('b='))
c=int(input('c='))

#設定常數 p
p=1.0675

import math
  
#表面積與體積計算公式
S=4*math.pi*(((a**p)*(b**p)+(a**p)*(c**p)+(b**p)*(c**p)/3)**(1/p))
M=(4/3)*math.pi*a*b*c

#輸出結果
print("\n\t\t表面積: %.2f (cm³)" %S)
print("\n\t\t體積: %.2f (cm³)" %M)