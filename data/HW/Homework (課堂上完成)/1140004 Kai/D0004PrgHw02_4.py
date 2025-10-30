a = input("身高(cm)=")
b = input("體重(kg)=")
a = int(a)
b = int(b)
f = a/100
c = b/(f*f)
d = (a-80)*0.7
e = (a-70)*0.6
print("bmi=",c)
print("男性理想體重=",d,"(kg)")
print("女性理想體重=",e,"(kg)")