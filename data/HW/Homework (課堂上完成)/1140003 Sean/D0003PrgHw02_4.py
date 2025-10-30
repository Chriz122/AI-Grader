print("---請輸入個人身高與體重---")
a=int(input("身高(cm)："))
b=int(input("體重(kg):"))
c=b/((a/100)*(a/100))
d=(a-80)*0.7
e=(a-70)*0.6
print("BMI=",c)
print("男生理想體重為:",d,"(kg)","女生理想體重為:",e,"(kg)")


