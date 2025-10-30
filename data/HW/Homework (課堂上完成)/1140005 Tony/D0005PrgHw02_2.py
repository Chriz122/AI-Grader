import math
a=float(input("赤道半徑沿x軸"))
b=float(input("赤道半徑沿y軸"))
c=float(input("極半徑沿z軸"))
d=4/3*math.pi*a*b*c
print("橢圓體積",d)
e=4*math.pi*(((a**1.0675)*(b**1.0675)+(a**1.0675)*(c**1.0675)+(b**1.0675)*(c**1.0675))/3)**(1/1.0675)
print("表面積",e)

