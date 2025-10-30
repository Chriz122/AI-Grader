a=input("輸入”一元二次方程式(ax^2+bx+c=0)”的 a=")
b=input("輸入”一元二次方程式(ax^2+bx+c=0)”的 b=")
c=input("輸入”一元二次方程式(ax^2+bx+c=0)”的 c=")
a=int(a)
b=int(b)
c=int(c)
d=b*-1+(b*b-4*a*c)**0.5
e=d/2*a
f=b*-1-(b*b-4*a*c)**0.5
g=f/2*a
print("解為=",e,g)