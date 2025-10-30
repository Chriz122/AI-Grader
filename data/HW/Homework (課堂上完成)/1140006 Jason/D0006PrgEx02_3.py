a,b,c=map(int,input("請輸入一元二次方程式ax²+bx+c的 a,b,c三個係數值:").split( ))
#(b**2)>=4*a*c
#計算公式解
s=(-b+(b**2-4*a*c)**0.5)/2*a
t=(-b-(b**2-4*a*c)**0.5)/2*a
print("兩個實數解為:",round(s),round(t))

   



