#由鍵盤輸入一元二次方程式的a, b, c三個係數值
# a,b,c=map(int, input(‘請輸入一元二次方程式的a, b, c三個係數值:’).split(‘,’)) #每筆資料以split()指定的符號來間隔
print('請輸入一元二次方程式(ax2+bx+c=0)的a, b, c三個係數值')
a=int(input('a='))
b=int(input('b='))
c=int(input('c='))

import math

#判別式 b² ≥ 4ac
disc = b**2 - 4*a*c

#計算兩個實數解
x=(-b+math.sqrt(disc))/(2*a)
y=(-b-math.sqrt(disc))/(2*a)

# 顯示結果
print('\n此方程式的兩個實數解為：')
print("\n\t\tx₁: %.2f " %x)
print("\n\t\tx₂: %.2f " %y)