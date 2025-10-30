import math
print("ax²+bx+c=0")
a=int(input("a="))
b=int(input("b="))
c=int(input("c="))

D=b**2-4*a*c

d=float(-b+ math.sqrt(D)/2*a)
e=float(-b- math.sqrt(D)/2*a)
print("兩個實數解",d,e)
